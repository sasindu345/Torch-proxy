"""
POST   /proxies             — Load proxies into pool (append or replace).
GET    /proxies             — Pool summary + per-proxy state.
GET    /proxies/{id}        — Single proxy detail with history.
GET    /proxies/{id}/history — Check history array.
DELETE /proxies             — Clear the pool, keep alerts.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from urllib.parse import urlsplit

from app.state import state, ProxyEntry
from app.services.alert_engine import evaluate_alerts

router = APIRouter()


def _extract_proxy_id(url: str) -> str:
    """Extract proxy ID from the last path segment of the URL."""
    # Use parsed path only, so query/fragment never pollute the ID.
    path = urlsplit(url).path.rstrip("/")
    return path.split("/")[-1] if path else ""


@router.post("/proxies")
async def load_proxies(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"error": "Malformed JSON"}, status_code=400)

    proxy_urls = body.get("proxies", [])
    replace = body.get("replace", False)

    new_proxies = []
    async with state.lock:
        if replace:
            state.proxies.clear()

        for url in proxy_urls:
            proxy_id = _extract_proxy_id(url)
            proxy = ProxyEntry(id=proxy_id, url=url, status="pending")
            state.proxies[proxy_id] = proxy
            new_proxies.append(proxy)

        # If we replaced the pool and there's an active alert,
        # re-evaluate immediately — the old failed proxies are gone
        if replace:
            event_type, alert = evaluate_alerts(state)
            # Note: we don't dispatch webhooks here — the monitor loop will
            # handle that after the next probe. But we DO resolve orphaned alerts.

        # Sync active alert with new pool state
        state.sync_active_alert_with_pool()

    # Signal the monitor to wake up and probe immediately
    state.proxy_change_event.set()

    return JSONResponse(
        content={
            "accepted": len(new_proxies),
            "proxies": [
                {"id": p.id, "url": p.url, "status": p.status}
                for p in new_proxies
            ],
        },
        status_code=201,
    )


@router.get("/proxies")
async def get_proxies():
    async with state.lock:
        proxies = list(state.proxies.values())
        total = len(proxies)
        up_count = sum(1 for p in proxies if p.status == "up")
        down_count = sum(1 for p in proxies if p.status == "down")
        failure_rate = (down_count / total) if total > 0 else 0.0

        # Sync active alert so GET /alerts matches these numbers
        state.sync_active_alert_with_pool()

        return {
            "total": total,
            "up": up_count,
            "down": down_count,
            "failure_rate": round(failure_rate, 4),
            "proxies": [
                {
                    "id": p.id,
                    "url": p.url,
                    "status": p.status,
                    "last_checked_at": p.last_checked_at,
                    "consecutive_failures": p.consecutive_failures,
                }
                for p in proxies
            ],
        }


@router.get("/proxies/{proxy_id}")
async def get_proxy(proxy_id: str):
    async with state.lock:
        proxy = state.proxies.get(proxy_id)
        if proxy is None:
            return JSONResponse(
                content={"error": f"Proxy '{proxy_id}' not found"},
                status_code=404,
            )

        return {
            "id": proxy.id,
            "url": proxy.url,
            "status": proxy.status,
            "last_checked_at": proxy.last_checked_at,
            "consecutive_failures": proxy.consecutive_failures,
            "total_checks": proxy.total_checks,
            "uptime_percentage": proxy.uptime_percentage,
            "history": [
                {"checked_at": h.checked_at, "status": h.status}
                for h in proxy.history
            ],
        }


@router.get("/proxies/{proxy_id}/history")
async def get_proxy_history(proxy_id: str):
    async with state.lock:
        proxy = state.proxies.get(proxy_id)
        if proxy is None:
            return JSONResponse(
                content={"error": f"Proxy '{proxy_id}' not found"},
                status_code=404,
            )

        return [
            {"checked_at": h.checked_at, "status": h.status}
            for h in proxy.history
        ]


@router.delete("/proxies")
async def delete_proxies():
    async with state.lock:
        state.proxies.clear()

        # Re-evaluate alerts immediately — pool is now empty,
        # so any active alert must be resolved
        evaluate_alerts(state)

    return Response(status_code=204)
