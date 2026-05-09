import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession() as session:
        url = "http://httpbin.org/redirect-to?url=http%3A%2F%2Fhttpbin.org%2Fpost&status_code=301"
        for _ in range(5):
            async with session.post(url, json={"a":1}, allow_redirects=False) as resp:
                print("Status:", resp.status)
                if resp.status in (301, 302):
                    url = resp.headers.get("Location")
                    print("Redirected to:", url)
                    continue
                print(await resp.text())
                break

asyncio.run(main())
