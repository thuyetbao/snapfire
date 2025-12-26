#!/bin/python3

# Global
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import asyncio
import statistics

# External
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(title="Latency Measurement API")

DATA_DIR = Path("./latency")


def parse_window(window: str) -> timedelta:
    try:
        value = int(window[:-1])
        unit = window[-1]
        if unit == "m":
            return timedelta(minutes=value)
        if unit == "h":
            return timedelta(hours=value)
    except Exception:
        pass
    raise HTTPException(status_code=400, detail="Invalid window format (use 5m, 1h)")


def percentile(values, p):
    if not values:
        return None
    k = int(len(values) * p / 100)
    return sorted(values)[min(k, len(values) - 1)]


async def read_records(method: str, cutoff: datetime):
    records = []

    if not DATA_DIR.exists():
        return records

    for file in sorted(DATA_DIR.rglob("*.jsonl")):
        # async-friendly file reading
        loop = asyncio.get_event_loop()
        lines = await loop.run_in_executor(None, file.read_text)

        for line in lines.splitlines():
            try:
                rec = json.loads(line)
                ts = datetime.fromisoformat(rec["ts"].replace("Z", "+00:00"))

                if ts >= cutoff and rec["method"] == method:
                    records.append(rec)

            except Exception:
                continue

    return records


@app.get("/latency")
async def query_latency(
    method: str = Query(default=...), # regex="^(icmp|tcp|http)$
    window: str = Query("5m"),
):
    now = datetime.now(timezone.utc)
    delta = parse_window(window)
    cutoff = now - delta

    records = await read_records(method, cutoff)

    if not records:
        return {
            "method": method,
            "window": window,
            "count": 0,
            "message": "No data"
        }

    successes = [r for r in records if r.get("success")]
    latencies = [r["latency_ms"] for r in successes]

    return {
        "method": method,
        "window": window,
        "count": len(records),
        "success_rate": round(len(successes) / len(records), 4),
        "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else None,
        "p95_latency_ms": percentile(latencies, 95),
        "max_latency_ms": max(latencies) if latencies else None,
    }
