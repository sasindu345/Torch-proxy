"""
Global in-memory state for ProxyMaze.
All data lives here — no database, no persistence.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class HistoryEntry:
    """A single health-check result."""
    checked_at: str  # ISO 8601 UTC
    status: str  # "up" or "down"


@dataclass
class ProxyEntry:
    """Represents a single proxy in the monitored pool."""
    id: str
    url: str
    status: str = "pending"  # "pending", "up", "down"
    last_checked_at: Optional[str] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    history: list[HistoryEntry] = field(default_factory=list)

    @property
    def uptime_percentage(self) -> float:
        if self.total_checks == 0:
            return 0.0
        up_count = sum(1 for h in self.history if h.status == "up")
        return round((up_count / self.total_checks) * 100, 1)


@dataclass
class Alert:
    """Represents an alert (active or resolved)."""
    alert_id: str
    status: str  # "active" or "resolved"
    failure_rate: float
    total_proxies: int
    failed_proxies: int
    failed_proxy_ids: list[str]
    threshold: float = 0.2
    fired_at: str = ""  # ISO 8601 UTC
    resolved_at: Optional[str] = None
    message: str = "Proxy pool failure rate exceeded threshold"


@dataclass
class Webhook:
    """A registered webhook receiver."""
    webhook_id: str
    url: str


@dataclass
class Integration:
    """A registered Slack or Discord integration."""
    integration_id: str
    type: str  # "slack" or "discord"
    webhook_url: str
    username: str = "ProxyWatch"
    events: list[str] = field(default_factory=lambda: ["alert.fired", "alert.resolved"])


class AppState:
    """
    Singleton holding all application state.
    Uses asyncio.Lock for safe concurrent access between monitor loop and API routes.
    """

    def __init__(self):
        self.lock = asyncio.Lock()

        # Event to signal the monitor loop that proxies changed (wake up immediately)
        self.proxy_change_event = asyncio.Event()

        # Config
        self.check_interval_seconds: int = 30
        self.request_timeout_ms: int = 5000

        # Proxy pool: keyed by proxy ID
        self.proxies: dict[str, ProxyEntry] = {}

        # Alerts: all alerts ever created (active + resolved)
        self.alerts: list[Alert] = []
        self.active_alert: Optional[Alert] = None

        # Webhooks
        self.webhooks: list[Webhook] = []

        # Integrations
        self.integrations: list[Integration] = []

        # Metrics
        self.total_checks: int = 0
        self.webhook_deliveries: int = 0
        # Dedup successful deliveries per transition per receiver
        self.delivery_success_keys: set[str] = set()

        # Monitor control
        self.monitor_task = None

    def get_pool_snapshot(self) -> tuple[int, int, float, list[str]]:
        """
        Compute live pool metrics from current proxy state.
        Returns (total_proxies, failed_proxies, failure_rate, failed_proxy_ids).
        Must be called while holding self.lock.
        """
        proxies = list(self.proxies.values())
        total = len(proxies)
        failed_ids = [p.id for p in proxies if p.status == "down"]
        down_count = len(failed_ids)
        failure_rate = (down_count / total) if total > 0 else 0.0
        return total, down_count, failure_rate, failed_ids

    def sync_active_alert_with_pool(self) -> None:
        """
        Update the active alert's dynamic fields to match the live pool state.
        This ensures GET /alerts and GET /proxies always agree.
        Must be called while holding self.lock.
        """
        if self.active_alert is None:
            return
        total, down_count, failure_rate, failed_ids = self.get_pool_snapshot()
        self.active_alert.total_proxies = total
        self.active_alert.failed_proxies = down_count
        self.active_alert.failure_rate = round(failure_rate, 4)
        self.active_alert.failed_proxy_ids = failed_ids


# Global singleton
state = AppState()
