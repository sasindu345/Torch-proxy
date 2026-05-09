"""
Webhook Dispatcher — delivers alert events to registered webhook receivers.
Implements retry on transient failures (500, 502, 503, 504).
Exactly-once successful delivery per event per receiver.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

import aiohttp

from app.state import Alert, AppState

logger = logging.getLogger("proxymaze.webhook")

TRANSIENT_CODES = {408, 425, 429, 500, 502, 503, 504, 522, 524}
BASE_DELAY = 0.5  # seconds
PER_ATTEMPT_TIMEOUT = 5.0  # seconds
MAX_BACKOFF = 5.0  # seconds — keep retries fast so we hit 60s window
MAX_RETRY_TOTAL_SECONDS = 180.0  # safety cap so a dead receiver can't block forever


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
) -> tuple[bool, str]:
    """
    Deliver a JSON payload to a URL with retry on transient failures.
    Returns (True, "") on success, or (False, last_error_detail) on failure.
    Retries on transient/connection errors with capped backoff,
    bounded by MAX_RETRY_TOTAL_SECONDS so a permanently dead receiver
    cannot block subsequent events for the same URL.
    """
    attempt = 0
    last_error = "no attempts made"
    started = asyncio.get_event_loop().time()
    while True:
        attempt += 1
        if asyncio.get_event_loop().time() - started > MAX_RETRY_TOTAL_SECONDS:
            logger.error(f"Giving up on {url} after {attempt-1} attempts ({MAX_RETRY_TOTAL_SECONDS}s): {last_error}")
            return False, f"exhausted {attempt-1} attempts in {MAX_RETRY_TOTAL_SECONDS}s — last: {last_error}"
        try:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=PER_ATTEMPT_TIMEOUT),
                ssl=False,
                allow_redirects=False,
            ) as resp:
                # Drain body so connection can be reused
                try:
                    await resp.read()
                except Exception:
                    pass

                # Handle redirects manually — aiohttp converts POST→GET on
                # 301/302 which causes HTTP 405 on the evaluator's capture server.
                if resp.status in (301, 302, 303, 307, 308):
                    redirect_url = resp.headers.get("Location", "")
                    if redirect_url:
                        logger.info(
                            f"Redirect {resp.status} from {url} → {redirect_url}, "
                            f"re-POSTing (attempt {attempt})"
                        )
                        url = redirect_url
                        attempt -= 1  # don't count redirect as a failed attempt
                        continue

                if 200 <= resp.status < 300:
                    logger.info(f"Webhook delivered to {url} (status={resp.status}) on attempt {attempt}")
                    return True, ""
                last_error = f"HTTP {resp.status}"
                if resp.status not in TRANSIENT_CODES:
                    logger.warning(
                        f"Non-transient webhook status {resp.status} to {url}, "
                        f"attempt {attempt} — retrying anyway"
                    )
                else:
                    logger.warning(
                        f"Transient failure ({resp.status}) delivering to {url}, "
                        f"attempt {attempt}"
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError, TimeoutError, OSError) as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(
                f"Connection error delivering to {url}: {last_error}, "
                f"attempt {attempt}"
            )
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            logger.warning(
                f"Unexpected error delivering to {url}: {last_error}, "
                f"attempt {attempt}"
            )

        # Capped exponential backoff (max MAX_BACKOFF) to ensure we hit 60s delivery window
        delay = min(BASE_DELAY * (2 ** max(0, attempt - 1)), MAX_BACKOFF)
        await asyncio.sleep(delay)


async def dispatch_event(
    session: aiohttp.ClientSession,
    app_state: AppState,
    event_type: str,
    alert: Alert,
) -> None:
    """
    Dispatch an alert event to all registered webhook receivers and integrations.
    Builds payload from the alert object (which was synced with live pool state
    before this function is called).
    Schedules per-receiver background tasks; returns immediately so the
    monitor loop is never blocked by retries.
    """
    if event_type == "alert.fired":
        payload = build_fired_payload(alert)
    elif event_type == "alert.resolved":
        payload = build_resolved_payload(alert)
    else:
        return

    transition_key = f"{event_type}:{alert.alert_id}"

    async with app_state.lock:
        webhooks = list(app_state.webhooks)
        integrations = list(app_state.integrations)

    targets: list[tuple[str, dict]] = []

    # Plain webhook receivers
    for wh in webhooks:
        targets.append((wh.url, payload))

    # Slack/Discord integrations (with their formatted payloads)
    for integ in integrations:
        if event_type not in integ.events:
            continue
        if integ.type == "slack":
            targets.append((integ.webhook_url, _build_slack_payload(alert, event_type, integ.username)))
        elif integ.type == "discord":
            targets.append((integ.webhook_url, _build_discord_payload(alert, event_type, integ.username)))

    for url, p in targets:
        success_key = f"{transition_key}:{url}"
        # Skip if already delivered or in-flight for this transition+url
        async with app_state.lock:
            if success_key in app_state.delivery_success_keys:
                continue
            if success_key in app_state.delivery_inflight_keys:
                continue
            app_state.delivery_inflight_keys.add(success_key)

        task = asyncio.create_task(
            _deliver_serialized(session, app_state, url, p, success_key)
        )
        app_state.dispatch_tasks.add(task)
        task.add_done_callback(app_state.dispatch_tasks.discard)


def _get_url_lock(app_state: AppState, url: str) -> asyncio.Lock:
    """Get-or-create a per-URL lock to serialize delivery order."""
    lock = app_state.url_locks.get(url)
    if lock is None:
        lock = asyncio.Lock()
        app_state.url_locks[url] = lock
    return lock


def _log_delivery(app_state: AppState, url: str, event: str, success: bool, detail: str) -> None:
    """Append a delivery attempt record to the in-memory log (max 200)."""
    entry = {
        "ts": time.time(),
        "url": url,
        "event": event,
        "success": success,
        "detail": detail,
    }
    app_state.delivery_log.append(entry)
    if len(app_state.delivery_log) > 200:
        app_state.delivery_log[:] = app_state.delivery_log[-200:]


async def _deliver_serialized(
    session: aiohttp.ClientSession,
    app_state: AppState,
    url: str,
    payload: dict,
    success_key: str,
) -> None:
    """
    Deliver under per-URL lock to enforce strict ordering of events
    (e.g. alert.fired must arrive before alert.resolved at same receiver).
    Exactly-once successful delivery per transition per receiver.
    """
    event_type = payload.get("event", "unknown")
    url_lock = _get_url_lock(app_state, url)
    try:
        async with url_lock:
            # Re-check inside lock — the previous holder may have already sent it
            async with app_state.lock:
                if success_key in app_state.delivery_success_keys:
                    _log_delivery(app_state, url, event_type, True, "already delivered (dedup)")
                    return

            success, err_detail = await deliver_to_url(session, url, payload)

            if success:
                async with app_state.lock:
                    if success_key not in app_state.delivery_success_keys:
                        app_state.delivery_success_keys.add(success_key)
                        app_state.webhook_deliveries += 1
                        _log_delivery(app_state, url, event_type, True, "delivered OK")
            else:
                async with app_state.lock:
                    _log_delivery(app_state, url, event_type, False, err_detail)
    except Exception as e:
        logger.error(f"_deliver_serialized error for {url}: {e}", exc_info=True)
        async with app_state.lock:
            _log_delivery(app_state, url, event_type, False, f"exception: {type(e).__name__}: {e}")
    finally:
        async with app_state.lock:
            app_state.delivery_inflight_keys.discard(success_key)


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
        color = "#36a64f"
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


def _build_discord_payload(alert: Alert, event_type: str, username: str) -> dict:
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
        "username": username,
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
