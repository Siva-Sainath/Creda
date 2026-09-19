#!/usr/bin/env bash
set -euo pipefail
: "${AWS_PROFILE:=creda-dev}"
: "${TELEGRAM_BOT_TOKEN:?Set TELEGRAM_BOT_TOKEN from @BotFather}"
: "${TELEGRAM_WEBHOOK_SECRET:?Set TELEGRAM_WEBHOOK_SECRET (openssl rand -hex 32)}"

ROOT="/Users/siva/Documents/first_commit_hack"
BACKEND="/Users/siva/Documents/Codex/2026-09-17/creda-aws-backend/outputs/creda-backend"
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
UI="${CREDA_UI_URL:-https://main.d32sg54oqu2gcb.amplifyapp.com}"

aws sts get-caller-identity --profile "$AWS_PROFILE" >/dev/null

echo "==> Deploy Telegram resources to creda-mumbai"
cd "$BACKEND"
sam build
sam deploy --stack-name creda-mumbai --region ap-south-1 \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --parameter-overrides \
    EnableBedrock=false EnableQwen=true \
    TelegramBotToken="$TELEGRAM_BOT_TOKEN" \
    TelegramWebhookSecret="$TELEGRAM_WEBHOOK_SECRET" \
    PublicApiUrl="$API" \
    PublicUiUrl="$UI" \
  --no-confirm-changeset --resolve-s3 --profile "$AWS_PROFILE"

echo "==> Register webhook"
export CREDA_API_URL="$API"
"$ROOT/scripts/setup_telegram_webhook.sh"

echo "==> Probe webhook route"
"$ROOT/scripts/test_telegram_webhook.sh"

echo "Done. Message @CredashieldBot with a pasted offer to smoke test."
