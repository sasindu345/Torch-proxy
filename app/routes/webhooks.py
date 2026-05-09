"""
POST /webhooks — Register a URL to receive alert webhook notifications.
"""

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.state import state, Webhook

router = APIRouter()


@router.post("/webhooks")
async def register_webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"error": "Malformed JSON"}, status_code=400)

    url = body.get("url")
    if not url:
        return JSONResponse(
            content={"error": "url field is required"},
            status_code=400,
        )

    webhook_id = f"wh-{uuid.uuid4().hex[:6]}"
    webhook = Webhook(webhook_id=webhook_id, url=url)
    async with state.lock:
        state.webhooks.append(webhook)

    return JSONResponse(
        content={
            "webhook_id": webhook.webhook_id,
            "url": webhook.url,
        },
        status_code=201,
    )
