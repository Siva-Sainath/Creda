#!/usr/bin/env bash
# Poll SageMaker endpoint; on success deploy ECS sagemaker backend and run smoke E2E.
set -euo pipefail
export PATH="/usr/local/bin:${PATH:-}"
PROFILE="${AWS_PROFILE:-creda-dev}"
REGION="${AWS_REGION:-ap-south-1}"
ENDPOINT="${CREDA_SM_ENDPOINT:-creda-qwen-judge}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
MAX_WAIT_MIN="${CREDA_SM_MAX_WAIT_MIN:-45}"

aws_cli() { aws --profile "$PROFILE" --region "$REGION" "$@"; }

echo "==> Waiting up to ${MAX_WAIT_MIN}m for $ENDPOINT"
deadline=$(( $(date +%s) + MAX_WAIT_MIN * 60 ))
status="Unknown"
while [[ $(date +%s) -lt $deadline ]]; do
  status=$(aws_cli sagemaker describe-endpoint --endpoint-name "$ENDPOINT" --query EndpointStatus --output text 2>/dev/null || echo Missing)
  echo "  $(date -u +%H:%M:%S) status=$status"
  if [[ "$status" == "InService" ]]; then
    break
  fi
  if [[ "$status" == "Failed" ]]; then
    reason=$(aws_cli sagemaker describe-endpoint --endpoint-name "$ENDPOINT" --query FailureReason --output text)
    echo "FAILED: $reason"
    echo "==> Retrying with gpu-3-1 AMI fix"
    CREDA_SM_FORCE=1 bash "$ROOT/scripts/deploy_sagemaker_judge.sh"
    deadline=$(( $(date +%s) + MAX_WAIT_MIN * 60 ))
    continue
  fi
  if [[ "$status" == "Missing" ]]; then
    bash "$ROOT/scripts/deploy_sagemaker_judge.sh"
  fi
  sleep 60
done

status=$(aws_cli sagemaker describe-endpoint --endpoint-name "$ENDPOINT" --query EndpointStatus --output text 2>/dev/null || echo Missing)
if [[ "$status" != "InService" ]]; then
  echo "SageMaker not ready after ${MAX_WAIT_MIN}m (status=$status). ECS stays on llama."
  exit 1
fi

echo "==> Smoke test SageMaker VLM invoke"
VENV="/tmp/creda-sm-venv"
"$VENV/bin/python" "$ROOT/infra/sagemaker/smoke_test_vlm.py" --endpoint "$ENDPOINT" || {
  echo "Smoke test failed; ECS stays on llama."
  exit 1
}

echo "==> Deploy ECS with SageMaker backend"
CREDA_JUDGE_BACKEND=sagemaker CREDA_QWEN_TAG="sm-$(date +%Y%m%d%H%M%S)" bash "$ROOT/scripts/deploy_qwen_ecs.sh"

echo "==> E2E"
CREDA_API_URL="$API" bash "$ROOT/scripts/test_e2e_full.sh"
echo "SageMaker wired and E2E complete."
