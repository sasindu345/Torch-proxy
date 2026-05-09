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
    Thread-safe via a lock for mutations from the monitor loop and API routes.
    """

    def __init__(self):
        self.lock = asyncio.Lock()

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
        # In-flight dedup: prevent concurrent dispatches for same transition+url
        self.delivery_inflight_keys: set[str] = set()
        # Per-URL locks to serialize delivery order (fired -> resolved -> ...)
        self.url_locks: dict[str, asyncio.Lock] = {}

        # Monitor control
        self.monitor_task = None
        # Background dispatch tasks (so we can await on shutdown)
        self.dispatch_tasks: set = set()


# Global singleton
state = AppState()
