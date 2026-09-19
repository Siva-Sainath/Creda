#!/usr/bin/env bash
set -euo pipefail
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
WEBHOOK="${API}/telegram/webhook"

echo "==> Route exists (expect 401 without secret, not 404)"
code=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "$WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{"update_id":1,"message":{"message_id":1,"chat":{"id":0,"type":"private"},"text":"probe"}}')
if [[ "$code" == "404" ]]; then
  echo "FAIL: webhook returns 404 — Telegram Lambdas not deployed"
  exit 1
fi
if [[ "$code" != "401" ]]; then
  echo "WARN: expected 401 without secret, got $code"
fi

if [[ -n "${TELEGRAM_WEBHOOK_SECRET:-}" ]]; then
  echo "==> Auth with secret (expect 200)"
  code=$(curl -sS -o /tmp/tg-webhook.json -w "%{http_code}" -X POST "$WEBHOOK" \
    -H "Content-Type: application/json" \
    -H "X-Telegram-Bot-Api-Secret-Token: ${TELEGRAM_WEBHOOK_SECRET}" \
    -d '{"update_id":999999,"message":{"message_id":1,"chat":{"id":0,"type":"private"},"text":"hi"}}')
  echo "HTTP $code $(cat /tmp/tg-webhook.json)"
  [[ "$code" == "200" ]] || exit 1
fi

echo "TELEGRAM WEBHOOK OK"
