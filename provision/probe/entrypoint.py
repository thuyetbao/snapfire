#!/bin/python3

# Global
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal
import re

# External
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import polars as pl
import polars.selectors as pl_sel
from pydantic import BaseModel, Field, computed_field, field_validator

# The data measurement jsonl file
DATA_MEASUREMENT_DATA_JSONL_PATH = os.environ.get("DATA_MEASUREMENT_DATA_JSONL_PATH", "/mnt/usr/application-probe/measurement.jsonl")
DATA_MEASUREMENT_DATA_JSONL_PATH = Path(DATA_MEASUREMENT_DATA_JSONL_PATH)

if not DATA_MEASUREMENT_DATA_JSONL_PATH.exists():
    raise FileNotFoundError(DATA_MEASUREMENT_DATA_JSONL_PATH)

# Build
app = FastAPI(
    title="Application Probe",
    description="The latency application for probe instance",
    version="0.1.8",
    openapi_url="/openapi.json",
    docs_url="/documentation",
    redoc_url=None,
    debug=False,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RequestParametersModel(BaseModel):
    protocol: Literal["icmp", "udp", "tcp", "http"] = Field(
        default="icmp",
        description="Protocol of latency measurement",
        examples=["icmp", "udp", "tcp", "http"],
        pattern=r"^(icmp|udp|tcp|http)$"
    )
    window: str = Field(
        default="5m",
        description="Window of latency measurement",
        examples=["5m", "1h", "1d"],
        pattern=r"^\d+(m|h|d)$"
    )

    @field_validator("protocol", "window", mode="before")
    def normalize_field(cls, value: str):
        return value.lower().strip()

    @computed_field
    @property
    def current(self) -> datetime:
        return datetime.now(timezone.utc)

    @computed_field
    @property
    def cutoff(self) -> datetime:
        return self.current - self.delta

    @computed_field
    @property
    def delta(self) -> timedelta:
        components = re.compile(r"^(?P<ref_value>\d+)(?P<ref_unit>m|h|d)$").match(self.window)
        ref_value, ref_unit = components["ref_value"], components["ref_unit"]
        if ref_unit == "m":
            return timedelta(minutes=int(ref_value))
        elif ref_unit == "h":
            return timedelta(hours=int(ref_value))
        elif ref_unit == "d":
            return timedelta(days=int(ref_value))


class ResponseLatencyModel(BaseModel):
    protocol: str = Field(default=None, description="Protocol of latency measurement")
    window: str = Field(default=None, description="Window of latency measurement")
    count: int = Field(default=None, description="Count of records")
    success_rate: float | None = Field(default=None, description="Success rate of latency measurement")
    p1_lantency_ms: float | None = Field(default=None, description="1st percentile latency in ms")
    p10_latency_ms: float | None = Field(default=None, description="10th percentile latency in ms")
    p25_latency_ms: float | None = Field(default=None, description="25th percentile latency in ms")
    p50_latency_ms: float | None = Field(default=None, description="50th percentile latency in ms")
    p75_latency_ms: float | None = Field(default=None, description="75th percentile latency in ms")
    p95_latency_ms: float | None = Field(default=None, description="95th percentile latency in ms")
    p99_latency_ms: float | None = Field(default=None, description="99th percentile latency in ms")
    max_latency_ms: float | None = Field(default=None, description="Maximum latency in ms")
    avg_latency_ms: float | None = Field(default=None, description="Average latency in ms")
    # {
    #   "percentiles": {
    #     "p50": { "value": 10.2, "unit": "ms" },
    #     "p99": { "value": 88.4, "unit": "ms" }
    #   },
    #   "stats": {
    #     "avg": { "value": 14.1, "unit": "ms" },
    #     "max": { "value": 140.0, "unit": "ms" }
    #   }
    # }


@app.get("/health")
async def getApplicationHealth():
    now = datetime.now(timezone.utc)
    return {
        "timestamp": now.isoformat(timespec="milliseconds", sep="T", sep_seconds=False, sep_milliseconds="Z"),
        "timezone": now.tzname(),
    }


@app.get(
    path="/metrics",
    summary="Fetch latency metrics",
    description="Fetch latency metrics statistics",
    response_model=ResponseLatencyModel,
)
async def fetchLatencyMetrics(
    query: Annotated[RequestParametersModel, Query()],
):

    # Search
    result = pl.scan_ndjson(
        source=DATA_MEASUREMENT_DATA_JSONL_PATH,
        schema={
            "timestamp": pl.String,
            "protocol": pl.String,
            "success": pl.Boolean,
            "latency_ms": pl.Float64,
        },
        infer_schema_length=None,
        low_memory=False,
        ignore_errors=True,
    ).filter(
        (pl.col("protocol") == query.protocol)
        &
        (pl.col("timestamp").str.to_datetime(time_zone="UTC") >= pl.lit(query.cutoff, pl.Datetime(time_zone="UTC")))
    ).select(
        pl.col("protocol"),
        pl.lit(query.window).cast(pl.String).alias("window"),
        pl.count().alias("count"),
        (pl.col("success").sum() / pl.count()).mul(100).alias("success_rate"),
        pl.col("latency_ms").filter(pl.col("success")).mean().alias("avg_latency_ms"),
        pl.col("latency_ms").filter(pl.col("success")).quantile(0.05).alias("p5_latency_ms"),
        pl.col("latency_ms").filter(pl.col("success")).quantile(0.1).alias("p10_latency_ms"),
        pl.col("latency_ms").filter(pl.col("success")).quantile(0.25).alias("p25_latency_ms"),
        pl.col("latency_ms").filter(pl.col("success")).quantile(0.5).alias("p50_latency_ms"),
        pl.col("latency_ms").filter(pl.col("success")).quantile(0.75).alias("p75_latency_ms"),
        pl.col("latency_ms").filter(pl.col("success")).quantile(0.95).alias("p95_latency_ms"),
        pl.col("latency_ms").filter(pl.col("success")).quantile(0.99).alias("p99_latency_ms"),
        pl.col("latency_ms").filter(pl.col("success")).max().alias("max_latency_ms"),
    ).with_columns(pl_sel.numeric().round(2)).collect()

    if result.is_empty():
        return {
            "protocol": query.protocol,
            "window": query.window,
            "count": 0,
        }

    return result.row(0, named=True)
