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
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"error": "Malformed JSON"}, status_code=400)

    async with state.lock:
        if "check_interval_seconds" in body:
            state.check_interval_seconds = int(body["check_interval_seconds"])
        if "request_timeout_ms" in body:
            state.request_timeout_ms = int(body["request_timeout_ms"])

        result = {
            "check_interval_seconds": state.check_interval_seconds,
            "request_timeout_ms": state.request_timeout_ms,
        }

    # Wake the monitor so it immediately uses the new interval
    state.proxy_change_event.set()

    return JSONResponse(content=result, status_code=200)


@router.get("/config")
async def get_config():
    async with state.lock:
        return {
            "check_interval_seconds": state.check_interval_seconds,
            "request_timeout_ms": state.request_timeout_ms,
        }
