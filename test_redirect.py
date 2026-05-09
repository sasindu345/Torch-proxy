import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.post("http://evaluator.torchproxies.com", json={"test": 1}) as resp:
            print("Status:", resp.status)
            print("URL:", resp.url)

asyncio.run(main())
