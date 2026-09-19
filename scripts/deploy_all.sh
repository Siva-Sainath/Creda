#!/usr/bin/env bash
set -euo pipefail
: "${AWS_PROFILE:=creda-dev}"
ROOT="/Users/siva/Documents/first_commit_hack"
BACKEND="/Users/siva/Documents/Codex/2026-09-17/creda-aws-backend/outputs/creda-backend"
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"

echo "==> AWS auth (run: aws login --profile $AWS_PROFILE if this fails; needs AWS CLI v2.32+)"
aws sts get-caller-identity --profile "$AWS_PROFILE" || {
  echo "AWS credentials expired. Log in with SSO, then rerun this script."
  exit 1
}

echo "==> Lambda / API"
cd "$BACKEND"
sam build
sam deploy --stack-name creda-mumbai --region ap-south-1 \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --parameter-overrides EnableBedrock=false EnableQwen=true \
  EvidencePrefix=bundles/creda-demo-2026-09-17 \
  PublicApiUrl="$API" \
  --no-confirm-changeset --resolve-s3 --profile "$AWS_PROFILE"

echo "==> Refresh ATS cache"
aws lambda invoke --function-name creda-mumbai-evidence-refresh --region ap-south-1 \
  --profile "$AWS_PROFILE" /tmp/creda-refresh.json
cat /tmp/creda-refresh.json

echo "==> SageMaker VLM judge (Qwen3.5-4B)"
bash "$ROOT/scripts/deploy_sagemaker_judge.sh"

echo "==> ECS judge worker (SageMaker backend)"
cd "$ROOT"
CREDA_JUDGE_BACKEND=sagemaker CREDA_QWEN_TAG="creda-$(date +%Y%m%d%H%M%S)" bash scripts/deploy_qwen_ecs.sh

echo "==> Amplify UI"
cd "$ROOT/frontend"
mkdir -p dist
cp index.html styles.css app.js dist/
sed -i '' "s|__CREDA_API_URL__|$API|g" dist/app.js
DEPLOY=$(aws amplify create-deployment --app-id d32sg54oqu2gcb --branch-name main --region ap-south-1 --profile "$AWS_PROFILE" --output json)
JOB=$(echo "$DEPLOY" | jq -r .jobId)
URL=$(echo "$DEPLOY" | jq -r .zipUploadUrl)
(cd dist && zip -r -q ../deploy.zip .)
curl -s -X PUT -T deploy.zip -H "Content-Type: application/zip" "$URL"
aws amplify start-deployment --app-id d32sg54oqu2gcb --branch-name main --job-id "$JOB" --region ap-south-1 --profile "$AWS_PROFILE"

echo "==> E2E"
"$ROOT/scripts/test_e2e_full.sh"
