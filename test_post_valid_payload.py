import asyncio
import aiohttp
from app.state import Alert
from app.services.webhook import deliver_to_url, build_fired_payload

async def main():
    alert = Alert(
        alert_id="alert-a1b2c3",
        status="active",
        failure_rate=0.3,
        total_proxies=10,
        failed_proxies=3,
        failed_proxy_ids=["px-103", "px-104", "px-105"],
        threshold=0.2,
        fired_at="2026-04-24T10:20:00Z",
        resolved_at=None,
        message="Proxy pool failure rate exceeded threshold"
    )
    payload = build_fired_payload(alert)

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        url = "http://evaluator.torchproxies.com/__capture/9551/capture/d7e42a4f-228f-4c7c-98b4-ae6939d49abd"
        success, err = await deliver_to_url(session, url, payload)
        print(f"Success: {success}, Error: {err}")

asyncio.run(main())
