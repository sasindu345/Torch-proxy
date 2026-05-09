"""
HTTP Prober — performs real HTTP health checks against proxy URLs.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import aiohttp

from app.state import HistoryEntry, ProxyEntry


async def probe_proxy(
    session: aiohttp.ClientSession,
    proxy: ProxyEntry,
    timeout_ms: int,
) -> None:
    """
    Probe a single proxy URL via HTTP GET.
    - 2xx within timeout → up
    - Timeout, connection error, 5xx → down
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    timeout = aiohttp.ClientTimeout(total=timeout_ms / 1000.0)

    try:
        async with session.get(proxy.url, timeout=timeout, ssl=False) as resp:
            if 200 <= resp.status < 300:
                new_status = "up"
            elif resp.status >= 500:
                new_status = "down"
            else:
                # 3xx, 4xx — treat as up (not a proxy failure)
                new_status = "up"
    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
    ):
        new_status = "down"

    # Update proxy state
    proxy.status = new_status
    proxy.last_checked_at = now
    proxy.total_checks += 1

    if new_status == "down":
        proxy.consecutive_failures += 1
    else:
        proxy.consecutive_failures = 0

    proxy.history.append(HistoryEntry(checked_at=now, status=new_status))


async def probe_all(
    session: aiohttp.ClientSession,
    proxies: list[ProxyEntry],
    timeout_ms: int,
) -> None:
    """Probe all proxies concurrently."""
    if not proxies:
        return
    tasks = [probe_proxy(session, p, timeout_ms) for p in proxies]
    await asyncio.gather(*tasks, return_exceptions=True)
