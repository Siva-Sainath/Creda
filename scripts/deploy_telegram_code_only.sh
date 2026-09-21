#!/usr/bin/env bash
# Update ONLY telegram Lambda code. Does not change environment variables / secrets.
set -euo pipefail
# WARNING: update-function-code replaces the ENTIRE deployment package.
# Always zip the full live src/ directory (telegram_bot.py + neighbors),
# never a lone telegram_bot.py, or imports like intake_channels will break.
: "${AWS_PROFILE:=creda-dev}"
REGION="${AWS_REGION:-ap-south-1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${TELEGRAM_SRC_DIR:-}"
REF="$ROOT/docs/reference/telegram_bot.py"

if [[ -z "$SRC" ]]; then
  # Prefer live SAM src if present on this machine
  CANDIDATES=(
    "/Users/siva/Documents/Codex/2026-09-17/creda-aws-backend/outputs/creda-backend/src"
    "$ROOT/docs/reference"
  )
  for c in "${CANDIDATES[@]}"; do
    if [[ -f "$c/telegram_bot.py" ]]; then SRC="$c"; break; fi
  done
fi

: "${SRC:?Set TELEGRAM_SRC_DIR to the directory containing telegram_bot.py (+ neighbors)}"

echo "==> Packaging from $SRC"
STAGE=$(mktemp -d)
cp -R "$SRC/." "$STAGE/"
# Always ship the hardened reference bot on top of live neighbors.
cp "$REF" "$STAGE/telegram_bot.py"
ZIP=/tmp/creda-telegram-bot-$$.zip
( cd "$STAGE" && zip -qr "$ZIP" . -x '*/__pycache__/*' '*.pyc' 'test_*' )
echo "==> Zip $(wc -c < "$ZIP") bytes"

aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$REGION" >/dev/null

for FN in creda-mumbai-telegram-webhook creda-mumbai-telegram-worker; do
  echo "==> update-function-code $FN"
  aws lambda update-function-code \
    --profile "$AWS_PROFILE" --region "$REGION" \
    --function-name "$FN" \
    --zip-file "fileb://$ZIP" \
    --query '{FunctionName:FunctionName,CodeSize:CodeSize,LastModified:LastModified}' \
    --output table
done

echo "Done. Env vars untouched. Smoke: DM @CredashieldBot /start and an injection string."
rm -rf "$STAGE"
