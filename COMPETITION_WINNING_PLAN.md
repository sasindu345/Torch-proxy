# ProxyMaze'26 Competition Winning Plan (Evaluator-Focused)

Goal: maximize evaluator score fast by implementing only what is tested and weighted most.

## Score-first priorities

- [~] `90 pts` Threshold breach alerts + webhook delivery
- [x] `45 pts` Proxy ingestion + continuous background monitoring
- [ ] `30 pts` Re-breach lifecycle integrity
- [x] `30 pts` Single failure behavior
- [x] `25 pts` Pool operations + observability
- [x] `20 pts` Alert resolution
- [x] `10 pts` Bootstrap + config
- [~] `+20 pts` Slack + Discord bonus

Passing score is `186`, target is `250+`.

## Hard rules we must not break

- [x] Monitoring runs continuously in background (not request-triggered).
- [x] Proxy status comes only from real HTTP probes.
- [x] `2xx => up`, `timeout/connection error/5xx => down`.
- [x] Alert fires at `failure_rate >= 0.20`, resolves at `< 0.20`.
- [x] Only one active alert at a time.
- [ ] New breach after resolve must create new `alert_id`.
- [x] `failed_proxy_ids` must exactly match currently down proxies.
- [x] `/proxies`, `/alerts`, webhook payload must tell same story.
- [x] Unknown JSON fields must be accepted and ignored.

## Step-by-step execution checklist

## Step 1: Lock correctness before features (start here)

- [x] Add safe shared-state handling between API routes and monitor loop.
- [x] Prevent race conditions when pool/config/alerts are read and updated.
- [x] Ensure proxy IDs are deterministic from URL last path segment.
- [x] Keep alerts archived even after pool replace/clear.

Acceptance:
- [x] No inconsistent counts in `/proxies` or `/alerts` during active checks.

## Step 2: Guarantee continuous monitoring behavior (45 pts + 30 pts)

- [x] Monitor loop uses current `check_interval_seconds` every cycle.
- [x] Newly added proxies start as `pending`, then auto-transition to `up/down`.
- [x] `GET /proxies` reflects latest background check (no on-demand probing).
- [x] `consecutive_failures`, `last_checked_at`, `total_checks`, `history` always updated.

Acceptance:
- [x] Add proxy -> status changes without calling any read endpoint.

## Step 3: Alert lifecycle integrity (90 pts + 30 pts + 20 pts)

- [x] Fire one alert when breach begins (`>= 0.20`).
- [x] Keep same active alert through continuous breach (no duplicates).
- [x] Resolve same alert when recovered (`< 0.20`).
- [ ] Re-breach creates brand-new `alert_id`.
- [ ] Preserve order: fired -> resolved -> fired(new).

Acceptance:
- [~] `/alerts` shows full lifecycle history correctly.

## Step 4: Webhook delivery reliability (biggest score block)

- [x] `POST /webhooks` registers receivers correctly.
- [x] Send JSON with `Content-Type: application/json`.
- [x] Deliver within 60 seconds of state transition.
- [x] Retry transient receiver failures (`500/502/503/504`) until success.
- [~] Ensure exactly one successful delivery per transition per receiver (no duplicates).

Acceptance:
- [x] With flaky receiver (returns 500 first), event eventually succeeds once.

## Step 5: Endpoint contract compliance (easy points, avoid penalties)

- [x] `GET /health` returns `{"status":"ok"}`.
- [x] `POST/GET /config` updates and returns runtime config immediately.
- [x] `POST /proxies` supports append/replace and ignores unknown fields.
- [x] `GET /proxies/{id}` and `/history` return `404` for unknown IDs.
- [x] `DELETE /proxies` clears pool but does not delete alert archive.
- [x] `GET /metrics` returns valid non-empty JSON with required counters.

Acceptance:
- [~] All endpoints behave exactly like contract examples.

## Step 6: Bonus Slack + Discord (+20)

- [x] `POST /integrations` accepts slack/discord.
- [x] Slack payload includes required `username`, `text`, `attachments`, `footer`, integer `ts`.
- [x] Discord payload includes required `embeds` fields and valid color integer.
- [x] Bonus payloads sent on `alert.fired` and `alert.resolved`.

Acceptance:
- [x] Receiver captures valid Slack/Discord schema fields.

## Step 7: Evaluator rehearsal (must-do before submission)

- [x] Run black-box checklist using only HTTP client calls.
- [x] Validate exact field names, timestamps in ISO8601 UTC, counts, and IDs.
- [~] Test edge cases: empty pool, pending-only pool, re-breach, webhook transient failures.
- [ ] Freeze stable run command and deployment instructions.

Acceptance:
- [~] Rehearsal passes without manual fixes.

## Fast execution order (no complexity)

1. Fix shared-state + monitor consistency.
2. Fix alert lifecycle transitions.
3. Fix webhook retry + exactly-once success behavior.
4. Tighten endpoint contract behavior.
5. Validate with rehearsal script.
6. Add Slack/Discord bonus polish.
7. Deploy to EC2 with stable startup.

## Developer Guidelines (simple rules)

- [ ] Do not add extra architecture now (no DB, no queue, no microservices) unless evaluator requires it.
- [ ] Every change must map to score points or contract compliance.
- [ ] After each code step, verify with curl before next step.
- [ ] Keep payload field names exactly as contract (no renaming).
- [ ] Ignore unknown fields in request JSON objects.
- [ ] Use UTC ISO 8601 timestamps (`YYYY-MM-DDTHH:MM:SSZ`).
- [ ] Never trigger checks from read endpoints; monitor loop only.
- [ ] Keep one active alert max; archive old alerts.

## Development Workflow (easy to follow)

1. Implement one scoring block.
2. Run related curl checks immediately.
3. Fix mismatches before moving on.
4. Update checklist status.
5. Repeat until all high-score blocks pass.

## Curl Test Checklist (evaluator-style)

- [x] `GET /health` -> `200` + `{\"status\":\"ok\"}`
- [x] `POST /config` then `GET /config` returns updated values
- [x] `POST /proxies` with `replace=true` returns pending proxies
- [x] Wait one interval then `GET /proxies` shows real up/down
- [x] `GET /proxies/{id}` includes required detailed fields
- [x] `GET /proxies/{id}/history` returns array
- [x] `GET /alerts` shows active alert on breach
- [x] `POST /webhooks` receiver gets `alert.fired`
- [x] transient 500 on receiver retries and succeeds
- [x] breach recovery leads to `alert.resolved`
- [ ] re-breach creates new `alert_id`
- [x] `DELETE /proxies` clears pool but keeps alerts
- [x] `GET /metrics` always returns valid non-empty JSON

## EC2 minimum deploy checklist (only what matters)

- [ ] App runs on `0.0.0.0:8080`.
- [ ] Security group allows evaluator access to API port/path via chosen entrypoint.
- [ ] Use process manager (`systemd`) to auto-restart on crash/reboot.
- [ ] Verify from outside server: `/health`, `/config`, `/proxies`.
- [ ] Keep logs available for quick incident checks.

## Execution log

- [x] Plan created.
- [x] Step 1 completed.
- [x] Step 2 completed.
- [~] Step 3 in progress.
- [x] Step 4 core completed.
- [x] Step 5 mostly completed.
- [~] Step 6 mostly completed.
- [~] Step 7 in progress.

## Current Test Confirmation (2026-05-09)

- Confirmed by curl: `/health`, `/config`, `/proxies`, `/proxies/{id}`, `/proxies/{id}/history`, `/alerts`, `/webhooks`, `/integrations`, `/metrics`, `DELETE /proxies`.
- Confirmed lifecycle: `alert.fired` generated on breach and `alert.resolved` generated on recovery.
- Confirmed webhook reliability: transient `500` retried and then delivered successfully.
- Confirmed payload checks: Slack and Discord required structural fields present.
- Remaining to confirm: re-breach creates new `alert_id` and strict no-duplicate successful delivery across all retry patterns.
