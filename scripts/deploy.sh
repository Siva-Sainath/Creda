#!/usr/bin/env bash
# Judge-ready deploy sequence — run from repo root with AWS credentials configured.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> 1/5 Build local curated data (if stale, skip if recent)"
if [ ! -f data/curated/evidence.jsonl ]; then
  .venv/bin/python scripts/run_etl.py >/dev/null
fi

echo "==> 2/5 Build deploy bundle (small Lambda-friendly files)"
.venv/bin/python scripts/build_deploy_bundle.py

echo "==> 3/5 Prepare Lambda packages (copy shared/)"
bash scripts/prepare_lambdas.sh

echo "==> 4/5 SAM build + deploy"
cd infra
sam build --use-container 2>/dev/null || sam build
sam deploy --guided "$@" || sam deploy --no-confirm-changeset --no-fail-on-empty-changeset

BUCKET=$(aws cloudformation describe-stacks --stack-name creda --query "Stacks[0].Outputs[?OutputKey=='DataBucketName'].OutputValue" --output text 2>/dev/null || true)
if [ -z "$BUCKET" ]; then
  echo "Set BUCKET manually from stack outputs"
  read -r BUCKET
fi

echo "==> 5/5 Upload deploy bundle to S3"
cd "$ROOT"
.venv/bin/python scripts/upload_deploy_bundle.py --bucket "$BUCKET"

API=$(aws cloudformation describe-stacks --stack-name creda --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text 2>/dev/null || echo "see stack outputs")
echo ""
echo "Deploy complete."
echo "  API: $API"
echo "  Health: $API/health  (must show dataReady: true)"
echo "  Frontend: connect Amplify to frontend/ and set VITE_API_URL=$API"
echo ""
echo "Demo: open frontend, click a demo button, hit Check offer."
