"""
GET /metrics — Operational monitoring data.
"""

from fastapi import APIRouter

from app.state import state

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    return {
        "total_checks": state.total_checks,
        "current_pool_size": len(state.proxies),
        "active_alerts": 1 if state.active_alert is not None else 0,
        "total_alerts": len(state.alerts),
        "webhook_deliveries": state.webhook_deliveries,
    }
