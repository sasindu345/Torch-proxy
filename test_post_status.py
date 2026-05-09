import asyncio
import aiohttp
from app.state import Alert
from app.services.webhook import build_fired_payload

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
        async with session.post(url, json=payload, allow_redirects=False) as resp:
            print("Status:", resp.status)
            if resp.status in (301, 302):
                redirect = resp.headers.get("Location")
                print("Redirecting to:", redirect)
                async with session.post(redirect, json=payload) as resp2:
                    print("Status2:", resp2.status)
                    print("Body:", await resp2.text())

asyncio.run(main())
