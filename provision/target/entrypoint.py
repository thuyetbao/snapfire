#!/bin/python3

# Global
from datetime import datetime, timezone

# External
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Build
app = FastAPI(
    title="Application Target",
    description="The HTTP application for target instance",
    version="0.1.1",
    openapi_url="/openapi.json",
    docs_url="/documentation",
    redoc_url=None,
    debug=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/_/health")
async def getHealth():
    now = datetime.now(timezone.utc)
    return {
        "timestamp": now.isoformat(timespec="milliseconds", sep="T", sep_seconds=False, sep_milliseconds="Z"),
        "timezone": now.tzname(),
    }
