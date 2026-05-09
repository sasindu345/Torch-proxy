#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://65.1.35.247}"

echo "Running smoke test against: $BASE_URL"

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
    echo "Assertion failed. Expected body to contain: $expected"
    echo "Actual body: $body"
    exit 1
  fi
}

health="$(req GET /health)"
must_contain "$health" "\"status\":\"ok\""
echo "OK /health"

cfg_set="$(req POST /config '{"check_interval_seconds":5,"request_timeout_ms":1200}')"
must_contain "$cfg_set" "\"check_interval_seconds\":5"
must_contain "$cfg_set" "\"request_timeout_ms\":1200"
echo "OK POST /config"

cfg_get="$(req GET /config)"
must_contain "$cfg_get" "\"check_interval_seconds\":5"
must_contain "$cfg_get" "\"request_timeout_ms\":1200"
echo "OK GET /config"

proxies_set="$(req POST /proxies '{"proxies":["https://example.com/proxy/px-101","https://example.com/proxy/px-102"],"replace":true}')"
must_contain "$proxies_set" "\"accepted\":2"
echo "OK POST /proxies"

proxies_get="$(req GET /proxies)"
must_contain "$proxies_get" "\"total\":2"
must_contain "$proxies_get" "\"proxies\""
echo "OK GET /proxies"

proxy_single="$(req GET /proxies/px-101)"
must_contain "$proxy_single" "\"id\":\"px-101\""
echo "OK GET /proxies/{id}"

history="$(req GET /proxies/px-101/history)"
must_contain "$history" "["
echo "OK GET /proxies/{id}/history"

metrics="$(req GET /metrics)"
must_contain "$metrics" "\"current_pool_size\":2"
echo "OK GET /metrics"

alerts="$(req GET /alerts)"
must_contain "$alerts" "["
echo "OK GET /alerts"

delete_code="$(curl -sS -o /tmp/proxymaze_del.out -w '%{http_code}' -X DELETE "$BASE_URL/proxies")"
if [[ "$delete_code" != "204" ]]; then
  echo "Assertion failed. Expected DELETE /proxies status 204, got $delete_code"
  exit 1
fi
echo "OK DELETE /proxies"

echo "Smoke test passed."
