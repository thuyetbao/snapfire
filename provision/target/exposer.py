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
    version="0.1.2",
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


@app.get("/_/health")
async def getApplicationHealth():
    now = datetime.now(timezone.utc)
    return {
        "timestamp": now.isoformat(timespec="milliseconds", sep="T").replace("+00:00", "Z"),
        "timezone": now.tzname(),
    }
