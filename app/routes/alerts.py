"""
GET /alerts — The Alert Archive. Returns all alerts (active + resolved).
"""

from fastapi import APIRouter

from app.state import state

router = APIRouter()


@router.get("/alerts")
async def get_alerts():
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
