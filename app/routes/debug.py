"""
GET /debug — Remote diagnostic endpoint for deployed instances.
Shows internal state, delivery logs, and boot time.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app.state import state

router = APIRouter()


@router.get("/debug")
async def debug_state():
    async with state.lock:
        webhooks = [{"webhook_id": wh.webhook_id, "url": wh.url} for wh in state.webhooks]
        integrations = [
            {
                "integration_id": integ.integration_id,
                "type": integ.type,
                "webhook_url": integ.webhook_url,
                "events": integ.events,
            }
            for integ in state.integrations
        ]
        alerts = [
            {
                "alert_id": a.alert_id,
                "status": a.status,
                "failure_rate": a.failure_rate,
                "fired_at": a.fired_at,
                "resolved_at": a.resolved_at,
            }
            for a in state.alerts
        ]
        active_alert_id = state.active_alert.alert_id if state.active_alert else None
        delivery_success = list(state.delivery_success_keys)
        delivery_inflight = list(state.delivery_inflight_keys)
        dispatch_task_count = len(state.dispatch_tasks)
        delivery_log = list(state.delivery_log[-100:])
        proxy_count = len(state.proxies)
        config = {
            "check_interval_seconds": state.check_interval_seconds,
            "request_timeout_ms": state.request_timeout_ms,
        }

    uptime_seconds = round(time.time() - state.boot_time, 1)
    boot_utc = datetime.fromtimestamp(state.boot_time, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    return {
        "boot_time_utc": boot_utc,
        "uptime_seconds": uptime_seconds,
        "config": config,
        "proxy_count": proxy_count,
        "webhooks": webhooks,
        "integrations": integrations,
        "alerts": alerts,
        "active_alert_id": active_alert_id,
        "delivery_success_keys": delivery_success,
        "delivery_inflight_keys": delivery_inflight,
        "dispatch_task_count": dispatch_task_count,
        "delivery_log": delivery_log,
    }
