import json
from app.state import Alert
from app.services.webhook import build_fired_payload

alert = Alert(
    alert_id="alert-a1b2c3",
    status="active",
    failure_rate=0.3,
    total_proxies=10,
    failed_proxies=3,
    failed_proxy_ids=["px-103", "px-104", "px-105"],
    threshold=0.2,
    fired_at="2026-04-24T10:20:00Z",
    resolved_at=None,
    message="Proxy pool failure rate exceeded threshold"
)

payload = build_fired_payload(alert)
print(json.dumps(payload, indent=2))
