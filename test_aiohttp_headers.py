import asyncio
import aiohttp
from aiohttp import web

async def handle(request):
    print("Headers received:")
    for k, v in request.headers.items():
        print(f"  {k}: {v}")
    return web.json_response({"status": "ok"})

async def start_server():
    app = web.Application()
    app.router.add_post('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 9999)
    await site.start()
    return runner

async def main():
    runner = await start_server()
    async with aiohttp.ClientSession() as session:
        print("\n=== Testing json=payload ===")
        async with session.post("http://localhost:9999/", json={"test": 1}) as resp:
            pass
            
    await runner.cleanup()

asyncio.run(main())
