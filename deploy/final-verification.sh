#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://proxymazegmora.duckdns.org}"
REPO="${2:-Oxshadha/Torch-proxy}"

echo "== Final verification for $BASE_URL =="

req() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  if [[ -n "$data" ]]; then
    curl -sS -X "$method" "$BASE_URL$path" -H "Content-Type: application/json" -d "$data"
  else
    curl -sS -X "$method" "$BASE_URL$path"
  fi
}

must_contain() {
  local body="$1"
  local expected="$2"
  if [[ "$body" != *"$expected"* ]]; then
    echo "FAILED: expected '$expected' in: $body"
    exit 1
  fi
}

echo "1) Checking latest GitHub Actions status (CI + Deploy)"
if command -v gh >/dev/null 2>&1; then
  gh run list --repo "$REPO" --limit 6 || true
else
  echo "WARN: gh not found, skipping Actions check"
fi

echo "2) Basic health/config"
health="$(req GET /health)"
must_contain "$health" "\"status\":\"ok\""
echo "OK /health"

cfg="$(req GET /config)"
must_contain "$cfg" "\"check_interval_seconds\""
must_contain "$cfg" "\"request_timeout_ms\""
echo "OK /config"

echo "3) Set fast cadence for lifecycle checks"
cfg_set="$(req POST /config '{"check_interval_seconds":2,"request_timeout_ms":1200}')"
must_contain "$cfg_set" "\"check_interval_seconds\":2"
echo "OK POST /config"

echo "4) Breach -> Resolve -> Re-breach lifecycle"
req POST /proxies '{"proxies":["https://example.com/proxy/px-up1","http://127.0.0.1:9/proxy/px-down1"],"replace":true}' >/dev/null
sleep 5
alerts1="$(req GET /alerts)"
must_contain "$alerts1" "\"status\":\"active\""
echo "OK breach active alert"

req POST /proxies '{"proxies":["https://example.com/proxy/px-up2"],"replace":true}' >/dev/null
sleep 5
alerts2="$(req GET /alerts)"
must_contain "$alerts2" "\"status\":\"resolved\""
echo "OK resolve alert"

req POST /proxies '{"proxies":["https://example.com/proxy/px-up3","http://127.0.0.1:9/proxy/px-down2"],"replace":true}' >/dev/null
sleep 5
alerts3="$(req GET /alerts)"
must_contain "$alerts3" "\"status\":\"active\""
echo "OK re-breach active alert"

echo "5) Metrics and cleanup"
metrics="$(req GET /metrics)"
must_contain "$metrics" "\"total_checks\""
echo "OK /metrics"

code="$(curl -sS -o /tmp/proxy_final_del.out -w '%{http_code}' -X DELETE "$BASE_URL/proxies")"
if [[ "$code" != "204" ]]; then
  echo "FAILED: expected DELETE /proxies 204, got $code"
  exit 1
fi
echo "OK DELETE /proxies"

echo "== FINAL VERIFICATION PASSED =="
