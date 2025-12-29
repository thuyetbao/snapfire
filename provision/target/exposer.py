#!/bin/python3

# Global
from datetime import datetime, timezone

# External
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

# Build
app = FastAPI(
    title="Target",
    description="The HTTP application of Target member",
    version="0.3.9",
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


@app.get(
    path="/_/health",
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
