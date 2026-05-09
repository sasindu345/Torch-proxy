import asyncio
import aiohttp
from app.services.webhook import deliver_to_url

async def main():
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        success, err = await deliver_to_url(
            session,
            "http://evaluator.torchproxies.com/__capture/9551/capture/d7e42a4f-228f-4c7c-98b4-ae6939d49abd",
            {"event": "test"}
        )
        print(f"Success: {success}, Error: {err}")

asyncio.run(main())
