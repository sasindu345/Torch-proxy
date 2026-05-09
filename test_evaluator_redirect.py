import asyncio
import aiohttp

async def main():
    url = "http://evaluator.torchproxies.com/__capture/9803/capture/4073c22c-59ef-4d4d-b6e9-5ee63641fc11"
    async with aiohttp.ClientSession() as session:
        # Without allow_redirects=True
        async with session.post(url, json={"test": 1}) as resp:
            print("Status without redirect:", resp.status)
        
        # With allow_redirects=True
        async with session.post(url, json={"test": 1}, allow_redirects=True) as resp:
            print("Status with redirect:", resp.status)

asyncio.run(main())
