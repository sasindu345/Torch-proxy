"""
GET /alerts — The Alert Archive. Returns all alerts (active + resolved).

CONSISTENCY RULE: The active alert's dynamic fields (failed_proxy_ids,
failed_proxies, total_proxies, failure_rate) must agree exactly with
GET /proxies. We sync the active alert with the live pool before responding.
"""

from fastapi import APIRouter

from app.state import state

router = APIRouter()


@router.get("/alerts")
async def get_alerts():
    async with state.lock:
        # Sync active alert with live pool state to ensure consistency
        # with GET /proxies endpoint
        state.sync_active_alert_with_pool()

        return [
            {
                "alert_id": a.alert_id,
                "status": a.status,
                "failure_rate": a.failure_rate,
                "total_proxies": a.total_proxies,
                "failed_proxies": a.failed_proxies,
                "failed_proxy_ids": list(a.failed_proxy_ids),
                "threshold": a.threshold,
                "fired_at": a.fired_at,
                "resolved_at": a.resolved_at,
                "message": a.message,
            }
            for a in state.alerts
        ]
