import asyncio
from aiohttp import web

async def handle(request):
    data = await request.json()
    print(f"WEBHOOK RECEIVED: {data['event']} for {data.get('alert_id')}")
    return web.json_response({"status": "ok"})

app = web.Application()
app.router.add_post('/', handle)

if __name__ == '__main__':
    web.run_app(app, port=9999)
