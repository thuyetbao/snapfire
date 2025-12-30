#!/bin/python3

# Global
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal
import re
import uuid

# External
from fastapi import FastAPI, status, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import polars as pl
import polars.selectors as ps
from pydantic import BaseModel, Field, computed_field, field_validator, ConfigDict

# The data measurement jsonl file
DATA_MEASUREMENT_DATA_JSONL_PATH = os.environ.get("DATA_MEASUREMENT_DATA_JSONL_PATH", "/mnt/usr/application-probe/measurement.jsonl")

# Build
app = FastAPI(
    title="Probe",
    description="The agent of Probe member",
    version="0.4.12",
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


class _MesurementUnitModel(BaseModel):
    value: float | None = Field(default=None, description="Value of measurement feature")
    unit: str = Field(default="ms", description="Unit of measurement feature")
    first_seen: datetime | None = Field(default=None, description="First seen of measurement feature")
    last_seen: datetime | None = Field(default=None, description="First seen of measurement feature")


class _GroupPercentileModel(BaseModel):
    p1: _MesurementUnitModel | None = Field(default=None, description="1st percentile")
    p5: _MesurementUnitModel | None = Field(default=None, description="5th percentile")
    p10: _MesurementUnitModel | None = Field(default=None, description="10th percentile")
    p25: _MesurementUnitModel | None = Field(default=None, description="25th percentile")
    p50: _MesurementUnitModel | None = Field(default=None, description="50th percentile")
    p75: _MesurementUnitModel | None = Field(default=None, description="75th percentile")
    p90: _MesurementUnitModel | None = Field(default=None, description="90th percentile")
    p95: _MesurementUnitModel | None = Field(default=None, description="95th percentile")
    p99: _MesurementUnitModel | None = Field(default=None, description="99th percentile")


class _GroupStatsModel(BaseModel):
    min: _MesurementUnitModel | None = Field(default=None, description="Minimum latency")
    max: _MesurementUnitModel | None = Field(default=None, description="Maximum latency")
    avg: _MesurementUnitModel | None = Field(default=None, description="Average latency")
    med: _MesurementUnitModel | None = Field(default=None, description="Median latency")


class _GroupObservationModel(BaseModel):
    count: int = Field(default=None, description="Count of records")
    success_rate: float | None = Field(default=None, description="Success rate of latency measurement")


class ResponseLatencyModel(BaseModel):
    response_id: str = Field(default_factory=lambda: uuid.uuid4().hex, description="Response ID")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), description="Timestamp of returned data")
    status: str = Field(default=..., description="Status of returned data")
    parameters: dict[str, str] = Field(default_factory=dict, description="Parameters of latency measurement")
    observation: _GroupObservationModel | None = Field(default=None, description="Observation of latency measurement")
    percentile: _GroupPercentileModel | None = Field(default=None, description="Percentiles of latency measurement")
    stats: _GroupStatsModel | None = Field(default=None, description="Stats of latency measurement")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "response_id": "9b609b6aa7d44244a216847b37568606",
                    "timestamp": "2022-07-26T12:34:56.321Z",
                    "status": "success",
                    "parameters": {
                        "protocol": "icmp",
                        "window": "5m"
                    },
                    "observation": {
                        "count": 10,
                        "success_rate": 0.8
                    },
                    "percentile": {
                        "p25": {"value": 8.3, "unit": "ms"},
                        "p50": {"value": 10.2, "unit": "ms"},
                        "p75": {"value": 12.1, "unit": "ms"},
                        "p90": {"value": 14.5, "unit": "ms"},
                        "p95": {"value": 17.8, "unit": "ms"},
                        "p99": {"value": 88.4, "unit": "ms"}
                    },
                    "stats": {
                        "min": {"value": 5.8, "unit": "ms"},
                        "max": {"value": 140.0, "unit": "ms"},
                        "avg": {"value": 14.1, "unit": "ms"},
                        "med": {"value": 12.1, "unit": "ms"}
                    }
                }
            ]
        }
    )


@app.get(
    path="/health",
    tags=["Application"],
    summary="Get the application health",
    description="Get the application health",
    status_code=status.HTTP_200_OK,
)
async def getApplicationHealth():
    now = datetime.now(timezone.utc)
    return {
        "timestamp": now.isoformat(timespec="milliseconds", sep="T").replace("+00:00", "Z"),
        "timezone": now.tzname(),
    }


@app.get(
    path="/metrics",
    tags=["Mesurement"],
    summary="Fetch latency metrics",
    description="Fetch latency metrics statistics",
    status_code=status.HTTP_200_OK,
    response_model=ResponseLatencyModel,
)
async def fetchLatencyMetrics(
    query: Annotated[RequestParametersModel, Query()],
):

    # Build
    parameters = {"protocol": query.protocol, "window": query.window}

    # Handle
    if not Path(DATA_MEASUREMENT_DATA_JSONL_PATH).exists():
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "response_id": uuid.uuid4().hex,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "error",
                "detail": "Resource related to latency measurement not found",
                "parameters": parameters,
                "observation": None,
                "percentile": None,
                "stats": None
            }
        )

    # Search
    result = pl.scan_ndjson(
        source=Path(DATA_MEASUREMENT_DATA_JSONL_PATH),
        schema={
            "timestamp": pl.String,
            "protocol": pl.String,
            "status": pl.String,
            "duration_ms": pl.Float64,
        },
        infer_schema_length=None,
        low_memory=False,
        ignore_errors=True,
    ).filter(
        (pl.col("protocol") == query.protocol)
        &
        (pl.col("timestamp").str.to_datetime(time_zone="UTC") >= pl.lit(query.cutoff, pl.Datetime(time_zone="UTC")))
    ).with_columns(
        pl.col("timestamp").str.to_datetime(time_zone="UTC").name.keep(),
        pl.col("status").replace({"success": True, "error": False}, default=False, return_dtype=pl.Boolean).alias("is_success"),
        pl.col("status").replace({"success": False, "error": True}, default=False, return_dtype=pl.Boolean).alias("is_error"),
    ).select(
        pl.count().alias("count"),
        pl.when(pl.count() == 0)
            .then(None)
            .otherwise((pl.col("is_success").sum() / pl.count()).mul(100))
            .cast(pl.Float64)
            .alias("success_rate"),
        pl.col("timestamp").min().alias("first_seen"),
        pl.col("timestamp").max().alias("last_seen"),
        pl.col("duration_ms").filter(pl.col("is_success")).quantile(0.01).alias("p1_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).quantile(0.05).alias("p5_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).quantile(0.1).alias("p10_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).quantile(0.25).alias("p25_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).quantile(0.5).alias("p50_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).quantile(0.75).alias("p75_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).quantile(0.95).alias("p95_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).quantile(0.99).alias("p99_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).mean().alias("avg_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).median().alias("med_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).min().alias("min_duration_ms"),
        pl.col("duration_ms").filter(pl.col("is_success")).max().alias("max_duration_ms"),
    ).with_columns(ps.numeric().round(3)).collect()

    if result.is_empty():
        return {
            "status": "success",
            "parameters": parameters,
            "observation": {
                "count": 0,
            }
        }

    bundle = result.row(0, named=True)
    output = {
        "status": "success",
        "parameters": parameters,
        "observation": {
            "count": bundle["count"],
            "success_rate": bundle["success_rate"],
            "first_seen": bundle["first_seen"],
            "last_seen": bundle["last_seen"],
        },
        "percentile": {
            "p1": {"value": bundle["p1_duration_ms"], "unit": "ms"},
            "p5": {"value": bundle["p5_duration_ms"], "unit": "ms"},
            "p10": {"value": bundle["p10_duration_ms"], "unit": "ms"},
            "p25": {"value": bundle["p25_duration_ms"], "unit": "ms"},
            "p50": {"value": bundle["p50_duration_ms"], "unit": "ms"},
            "p75": {"value": bundle["p75_duration_ms"], "unit": "ms"},
            "p95": {"value": bundle["p95_duration_ms"], "unit": "ms"},
            "p99": {"value": bundle["p99_duration_ms"], "unit": "ms"},
        },
        "stats": {
            "min": {"value": bundle["min_duration_ms"], "unit": "ms"},
            "max": {"value": bundle["max_duration_ms"], "unit": "ms"},
            "avg": {"value": bundle["avg_duration_ms"], "unit": "ms"},
            "med": {"value": bundle["med_duration_ms"], "unit": "ms"}
        }
    }

    return output
