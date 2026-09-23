#!/usr/bin/env bash
# Deploy frontend zip to existing Amplify app (same URL, no new app).
set -euo pipefail
: "${AWS_PROFILE:=creda-dev}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_ID="d32sg54oqu2gcb"
BRANCH="main"
REGION="ap-south-1"

aws sts get-caller-identity --profile "$AWS_PROFILE" >/dev/null

cd "$ROOT/frontend"
mkdir -p dist
cp index.html styles.css app.js iso-loop.js iso-anim.js dist/
(cd dist && zip -r -q ../deploy.zip .)

DEPLOY=$(aws amplify create-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --region "$REGION" --profile "$AWS_PROFILE" --output json)
JOB=$(echo "$DEPLOY" | python3 -c "import sys,json; print(json.load(sys.stdin)['jobId'])")
URL=$(echo "$DEPLOY" | python3 -c "import sys,json; print(json.load(sys.stdin)['zipUploadUrl'])")
echo "Amplify job $JOB"
curl -sS -X PUT -T deploy.zip -H "Content-Type: application/zip" "$URL" -w "upload %{http_code}\n"
aws amplify start-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB" --region "$REGION" --profile "$AWS_PROFILE"
echo "Live: https://main.${APP_ID}.amplifyapp.com/"
