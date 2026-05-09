import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession() as session:
        # Register a local port as webhook
        webhook_url = "http://127.0.0.1:9998/webhook"
        await session.post("https://proxymazegmora.duckdns.org/webhooks", json={"url": webhook_url})
        
        # We need a listener for the webhook
        # We can just start one on the EC2 instance... wait we can't easily start a listener on EC2
        # Instead, let's use a public webhook like webhook.site, or since I can't read webhook.site programmatically easily, 
        # let's just use `evaluator.torchproxies.com` but wait, we don't control it.
        pass
