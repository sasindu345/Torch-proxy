"""
POST /config — Set runtime monitoring configuration.
GET /config  — Return current configuration.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.state import state

router = APIRouter()


@router.post("/config")
async def set_config(request: Request):
    body = await request.json()

    if "check_interval_seconds" in body:
        state.check_interval_seconds = int(body["check_interval_seconds"])
    if "request_timeout_ms" in body:
        state.request_timeout_ms = int(body["request_timeout_ms"])

    return JSONResponse(
        content={
            "check_interval_seconds": state.check_interval_seconds,
            "request_timeout_ms": state.request_timeout_ms,
        },
        status_code=200,
    )


@router.get("/config")
async def get_config():
    return {
        "check_interval_seconds": state.check_interval_seconds,
        "request_timeout_ms": state.request_timeout_ms,
    }
