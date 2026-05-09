"""
Alert Engine — manages the alert lifecycle: fire, resolve, re-breach.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.state import Alert, AppState


def evaluate_alerts(app_state: AppState) -> tuple[str | None, Alert | None]:
    """
    Evaluate the current pool and fire/resolve alerts as needed.
    MUST be called while holding app_state.lock.

    Returns:
        (event_type, alert) where event_type is "alert.fired", "alert.resolved", or None
    """
    proxies = list(app_state.proxies.values())
    total = len(proxies)

    if total == 0:
        # No proxies in pool — resolve any active alert
        if app_state.active_alert is not None:
            return _resolve_alert(app_state)
        return None, None

    # Only count proxies that have been checked (not pending)
    checked = [p for p in proxies if p.status in ("up", "down")]
    if not checked:
        # All proxies are still pending — no alert evaluation yet
        return None, None

    down_count = sum(1 for p in proxies if p.status == "down")
    failure_rate = down_count / total
    failed_ids = [p.id for p in proxies if p.status == "down"]

    if failure_rate >= 0.20:
        if app_state.active_alert is None:
            # FIRE a new alert
            return _fire_alert(app_state, failure_rate, total, down_count, failed_ids)
        else:
            # Breach continues — update the active alert's dynamic fields
            _sync_alert(app_state.active_alert, failure_rate, total, down_count, failed_ids)
            return None, None
    else:
        if app_state.active_alert is not None:
            # RESOLVE the active alert
            return _resolve_alert(app_state)
        return None, None


def _fire_alert(
    app_state: AppState,
    failure_rate: float,
    total: int,
    down_count: int,
    failed_ids: list[str],
) -> tuple[str, Alert]:
    """Create and fire a new alert."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    alert_id = f"alert-{uuid.uuid4().hex[:8]}"

    alert = Alert(
        alert_id=alert_id,
        status="active",
        failure_rate=round(failure_rate, 4),
        total_proxies=total,
        failed_proxies=down_count,
        failed_proxy_ids=failed_ids,
        threshold=0.2,
        fired_at=now,
        resolved_at=None,
        message="Proxy pool failure rate exceeded threshold",
    )

    app_state.alerts.append(alert)
    app_state.active_alert = alert
    return "alert.fired", alert


def _resolve_alert(app_state: AppState) -> tuple[str, Alert]:
    """Resolve the currently active alert."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    alert = app_state.active_alert
    alert.status = "resolved"
    alert.resolved_at = now
    # Clear dynamic fields on resolution
    alert.failed_proxies = 0
    alert.failed_proxy_ids = []
    app_state.active_alert = None
    return "alert.resolved", alert


def _sync_alert(
    alert: Alert,
    failure_rate: float,
    total: int,
    down_count: int,
    failed_ids: list[str],
) -> None:
    """Update an active alert's dynamic fields to reflect current pool state."""
    alert.failure_rate = round(failure_rate, 4)
    alert.total_proxies = total
    alert.failed_proxies = down_count
    alert.failed_proxy_ids = failed_ids
