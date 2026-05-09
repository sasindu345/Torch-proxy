"""
POST /integrations — Register Slack or Discord formatted alert integrations.
"""

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.state import state, Integration

router = APIRouter()


@router.post("/integrations")
async def register_integration(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"error": "Malformed JSON"}, status_code=400)

    integ_type = body.get("type")
    webhook_url = body.get("webhook_url")

    if not integ_type or not webhook_url:
        return JSONResponse(
            content={"error": "type and webhook_url are required"},
            status_code=400,
        )

    if integ_type not in ("slack", "discord"):
        return JSONResponse(
            content={"error": "type must be 'slack' or 'discord'"},
            status_code=400,
        )

    integration_id = f"integ-{uuid.uuid4().hex[:6]}"
    integration = Integration(
        integration_id=integration_id,
        type=integ_type,
        webhook_url=webhook_url,
        username=body.get("username", "ProxyWatch"),
        events=body.get("events", ["alert.fired", "alert.resolved"]),
    )
    async with state.lock:
        state.integrations.append(integration)

    return JSONResponse(
        content={
            "integration_id": integration.integration_id,
            "type": integration.type,
            "webhook_url": integration.webhook_url,
            "username": integration.username,
            "events": integration.events,
        },
        status_code=201,
    )
