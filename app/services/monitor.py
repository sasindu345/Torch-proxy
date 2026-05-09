"""
Background Monitor — continuously probes proxies on the configured cadence.
Runs as an asyncio task, independent of API requests.

KEY DESIGN:
- Uses proxy_change_event to wake up immediately when proxies are loaded/changed
- Probes on cadence set by check_interval_seconds
- After probing, evaluates alerts and dispatches webhooks
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from app.state import AppState
from app.services.prober import probe_all
from app.services.alert_engine import evaluate_alerts
from app.services.webhook import dispatch_event

logger = logging.getLogger("proxymaze.monitor")


async def monitoring_loop(app_state: AppState, session: aiohttp.ClientSession) -> None:
    """
    Continuous monitoring loop that:
    1. Waits for check_interval_seconds OR a proxy_change_event (whichever comes first)
    2. Probes all proxies concurrently
    3. Evaluates alert conditions
    4. Dispatches webhook events if state changed
    """
    logger.info("Background monitor started")

    while True:
        try:
            # Read interval fresh each cycle so config changes apply immediately
            async with app_state.lock:
                interval = app_state.check_interval_seconds

            # Wait for either: the interval to elapse, OR a proxy change signal
            # This ensures new proxies get checked immediately
            try:
                await asyncio.wait_for(
                    app_state.proxy_change_event.wait(),
                    timeout=interval,
                )
                # Event was set — proxies changed, clear it and probe immediately
                app_state.proxy_change_event.clear()
                logger.info("Proxy change detected — probing immediately")
            except asyncio.TimeoutError:
                # Normal cadence — interval elapsed, time for regular check
                pass

            # Get current proxy list
            async with app_state.lock:
                proxies = list(app_state.proxies.values())
                timeout_ms = app_state.request_timeout_ms

            if not proxies:
                continue

            # Probe all proxies concurrently
            await probe_all(session, proxies, timeout_ms)

            # Update metrics and evaluate alert conditions under lock
            async with app_state.lock:
                app_state.total_checks += len(proxies)

                # Evaluate alert conditions
                event_type, alert = evaluate_alerts(app_state)

                # Sync active alert with live pool (ensures consistency between
                # GET /alerts and GET /proxies during ongoing breach).
                app_state.sync_active_alert_with_pool()

            # Dispatch webhook if there's a state transition.
            # dispatch_event schedules per-receiver background tasks; it returns fast
            # so probing/state evaluation continues on the configured cadence.
            if event_type and alert:
                logger.info(f"Alert event: {event_type} — {alert.alert_id}")
                try:
                    await dispatch_event(session, app_state, event_type, alert)
                except Exception as e:
                    logger.error(f"dispatch_event failed: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("Background monitor cancelled")
            raise
        except Exception as e:
            logger.error(f"Monitor loop error: {e}", exc_info=True)
            # Don't crash the loop — wait and try again
            await asyncio.sleep(5)
