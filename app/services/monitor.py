"""
Background Monitor — continuously probes proxies on the configured cadence.
Runs as an asyncio task, independent of API requests.
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
    1. Waits check_interval_seconds
    2. Probes all proxies concurrently
    3. Evaluates alert conditions
    4. Dispatches webhook events if state changed
    """
    logger.info("Background monitor started")

    while True:
        try:
            # Read interval fresh each cycle so config changes apply immediately
            interval = app_state.check_interval_seconds
            await asyncio.sleep(interval)

            # Get current proxy list
            proxies = list(app_state.proxies.values())
            if not proxies:
                continue

            # Probe all proxies
            timeout_ms = app_state.request_timeout_ms
            await probe_all(session, proxies, timeout_ms)

            # Update metrics
            app_state.total_checks += len(proxies)

            # Evaluate alert conditions
            event_type, alert = evaluate_alerts(app_state)

            # Dispatch webhook if there's a state transition
            if event_type and alert:
                logger.info(f"Alert event: {event_type} — {alert.alert_id}")
                await dispatch_event(session, app_state, event_type, alert)

        except asyncio.CancelledError:
            logger.info("Background monitor cancelled")
            raise
        except Exception as e:
            logger.error(f"Monitor loop error: {e}", exc_info=True)
            # Don't crash the loop — wait and try again
            await asyncio.sleep(5)
