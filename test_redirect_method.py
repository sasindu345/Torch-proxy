import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession() as session:
        # RequestBin or httpbin to see what method it uses after redirect
        async with session.post("http://httpbin.org/redirect-to?url=http%3A%2F%2Fhttpbin.org%2Fpost&status_code=301", json={"a":1}, allow_redirects=True) as resp:
            print(resp.status)
            print(await resp.text())

asyncio.run(main())
