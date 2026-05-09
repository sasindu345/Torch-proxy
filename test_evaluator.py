import asyncio
import aiohttp

async def main():
    payload = {
        "event": "alert.fired",
        "alert_id": "alert-test",
        "fired_at": "2026-05-09T10:17:15Z",
        "failure_rate": 1.0,
        "total_proxies": 2,
        "failed_proxies": 2,
        "failed_proxy_ids": ["1", "2"],
        "threshold": 0.2,
        "message": "test"
    }
    url = "https://evaluator.torchproxies.com/__capture/9803/capture/4073c22c-59ef-4d4d-b6e9-5ee63641fc11"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as resp:
            print("Status HTTPS:", resp.status)

    url_http = "http://evaluator.torchproxies.com/__capture/9803/capture/4073c22c-59ef-4d4d-b6e9-5ee63641fc11"
    async with aiohttp.ClientSession() as session:
        async with session.post(url_http, json=payload, headers={"Content-Type": "application/json"}) as resp:
            print("Status HTTP:", resp.status)

asyncio.run(main())
