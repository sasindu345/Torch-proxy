import asyncio
import aiohttp
from app.services.webhook import deliver_to_url, build_fired_payload
from app.state import Alert
import json

async def main():
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        # Get the debug state
        async with session.get("https://proxymazegmora.duckdns.org/debug") as resp:
            data = await resp.json()
        
        if not data["alerts"]:
            print("No alerts found in debug.")
            return

        app_alert_dict = data["alerts"][0]
        
        # reconstruct the Alert object
        alert = Alert(
            alert_id=app_alert_dict["alert_id"],
            status=app_alert_dict["status"],
            failure_rate=app_alert_dict.get("failure_rate", 0.0), # debug endpoint might not have all fields
            total_proxies=data.get("proxy_count", 10),
            failed_proxies=int(data.get("proxy_count", 10) * app_alert_dict.get("failure_rate", 0.0)),
            failed_proxy_ids=["px-1", "px-2"], # mock
            threshold=0.2,
            fired_at=app_alert_dict["fired_at"],
            resolved_at=app_alert_dict["resolved_at"]
        )
        
        payload = build_fired_payload(alert)
        print("Payload:", json.dumps(payload, indent=2))
        
        url = data["webhooks"][0]["url"] if data["webhooks"] else None
        if not url:
            print("No webhook URL found.")
            return
            
        print("Testing against URL:", url)
        success, err = await deliver_to_url(session, url, payload)
        print(f"Success: {success}, Error: {err}")

asyncio.run(main())
