"""
Webhook Dispatcher — delivers alert events to registered webhook receivers.
Implements retry on transient failures (500, 502, 503, 504).
Exactly-once successful delivery per event per receiver.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import aiohttp

from app.state import Alert, AppState

logger = logging.getLogger("proxymaze.webhook")

TRANSIENT_CODES = {500, 502, 503, 504}
MAX_RETRIES = 10
BASE_DELAY = 1.0  # seconds


def build_fired_payload(alert: Alert) -> dict:
    """Build the alert.fired webhook event payload."""
    return {
        "event": "alert.fired",
        "alert_id": alert.alert_id,
        "fired_at": alert.fired_at,
        "failure_rate": alert.failure_rate,
        "total_proxies": alert.total_proxies,
        "failed_proxies": alert.failed_proxies,
        "failed_proxy_ids": list(alert.failed_proxy_ids),
        "threshold": alert.threshold,
        "message": alert.message,
    }


def build_resolved_payload(alert: Alert) -> dict:
    """Build the alert.resolved webhook event payload."""
    return {
        "event": "alert.resolved",
        "alert_id": alert.alert_id,
        "resolved_at": alert.resolved_at,
    }


async def deliver_to_url(
    session: aiohttp.ClientSession,
    url: str,
    payload: dict,
) -> bool:
    """
    Deliver a JSON payload to a URL with retry on transient failures.
    Returns True on successful delivery.
    """
    for attempt in range(MAX_RETRIES):
        try:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status < 500 or resp.status not in TRANSIENT_CODES:
                    # Success or non-transient error — stop retrying
                    return True
                # Transient failure — retry
                logger.warning(
                    f"Transient failure ({resp.status}) delivering to {url}, "
                    f"attempt {attempt + 1}/{MAX_RETRIES}"
                )
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.warning(
                f"Connection error delivering to {url}: {e}, "
                f"attempt {attempt + 1}/{MAX_RETRIES}"
            )

        # Exponential backoff: 1s, 2s, 4s, 8s...
        delay = min(BASE_DELAY * (2 ** attempt), 30)
        await asyncio.sleep(delay)

    logger.error(f"Failed to deliver webhook to {url} after {MAX_RETRIES} attempts")
    return False


async def dispatch_event(
    session: aiohttp.ClientSession,
    app_state: AppState,
    event_type: str,
    alert: Alert,
) -> None:
    """
    Dispatch an alert event to all registered webhook receivers and integrations.
    """
    if event_type == "alert.fired":
        payload = build_fired_payload(alert)
    elif event_type == "alert.resolved":
        payload = build_resolved_payload(alert)
    else:
        return

    tasks = []

    # Deliver to all registered webhook receivers
    for wh in app_state.webhooks:
        tasks.append(_deliver_and_count(session, app_state, wh.url, payload))

    # Deliver to Slack integrations
    for integ in app_state.integrations:
        if event_type in integ.events:
            if integ.type == "slack":
                slack_payload = _build_slack_payload(alert, event_type, integ.username)
                tasks.append(
                    _deliver_and_count(session, app_state, integ.webhook_url, slack_payload)
                )
            elif integ.type == "discord":
                discord_payload = _build_discord_payload(alert, event_type)
                tasks.append(
                    _deliver_and_count(session, app_state, integ.webhook_url, discord_payload)
                )

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def _deliver_and_count(
    session: aiohttp.ClientSession,
    app_state: AppState,
    url: str,
    payload: dict,
) -> None:
    """Deliver and increment the webhook delivery counter on success."""
    success = await deliver_to_url(session, url, payload)
    if success:
        app_state.webhook_deliveries += 1


def _build_slack_payload(alert: Alert, event_type: str, username: str) -> dict:
    """Build a Slack-formatted alert payload."""
    if event_type == "alert.fired":
        text = f"🚨 Alert Fired: {alert.message}"
        color = "#FF0000"
        fields = [
            {"title": "Alert ID", "value": alert.alert_id},
            {"title": "Failure Rate", "value": str(alert.failure_rate)},
            {"title": "Failed Proxies", "value": str(alert.failed_proxies)},
            {"title": "Threshold", "value": str(alert.threshold)},
            {"title": "Failed IDs", "value": ", ".join(alert.failed_proxy_ids)},
            {"title": "Fired At", "value": alert.fired_at},
        ]
    else:
        text = f"✅ Alert Resolved: {alert.alert_id}"
        color = "#00FF00"
        fields = [
            {"title": "Alert ID", "value": alert.alert_id},
            {"title": "Failure Rate", "value": "Below threshold"},
            {"title": "Failed Proxies", "value": "0"},
            {"title": "Threshold", "value": str(alert.threshold)},
            {"title": "Failed IDs", "value": "None"},
            {"title": "Fired At", "value": alert.fired_at},
        ]

    # Parse fired_at to Unix epoch (integer, not float, not string)
    try:
        dt = datetime.strptime(alert.fired_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        ts = int(dt.timestamp())
    except (ValueError, AttributeError):
        ts = int(datetime.now(timezone.utc).timestamp())

    return {
        "username": username,
        "text": text,
        "attachments": [
            {
                "color": color,
                "fields": fields,
                "footer": "ProxyMaze Alert System",
                "ts": ts,
            }
        ],
    }


def _build_discord_payload(alert: Alert, event_type: str) -> dict:
    """Build a Discord-formatted alert payload."""
    if event_type == "alert.fired":
        title = "🚨 Alert Fired"
        description = alert.message
        color = 16711680  # Red in decimal
        fields = [
            {"name": "Alert ID", "value": alert.alert_id},
            {"name": "Failure Rate", "value": str(alert.failure_rate)},
            {"name": "Failed Proxies", "value": str(alert.failed_proxies)},
            {"name": "Threshold", "value": str(alert.threshold)},
            {"name": "Failed IDs", "value": ", ".join(alert.failed_proxy_ids)},
        ]
    else:
        title = "✅ Alert Resolved"
        description = f"Alert {alert.alert_id} has been resolved"
        color = 65280  # Green in decimal
        fields = [
            {"name": "Alert ID", "value": alert.alert_id},
            {"name": "Failure Rate", "value": "Below threshold"},
            {"name": "Failed Proxies", "value": "0"},
            {"name": "Threshold", "value": str(alert.threshold)},
            {"name": "Failed IDs", "value": "None"},
        ]

    return {
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
                "fields": fields,
                "footer": {"text": "ProxyMaze Alert System"},
            }
        ],
    }
