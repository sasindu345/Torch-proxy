import asyncio
import aiohttp

async def main():
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get("https://httpbin.org/get") as resp:
                print("Status:", resp.status)
        except Exception as e:
            print("Error:", type(e).__name__, e)

asyncio.run(main())
