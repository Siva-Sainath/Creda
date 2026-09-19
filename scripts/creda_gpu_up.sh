#!/usr/bin/env bash
# Start GPU judge ASG (g4dn.xlarge desired=1) and deploy ECS GPU stack. ~$0.579/hr in ap-south-1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${AWS_PROFILE:-creda-dev}"
REGION="${AWS_REGION:-ap-south-1}"

echo "==> Deploy GPU ECS stack (g4dn.xlarge, vLLM + worker)"
CREDA_JUDGE_BACKEND=vllm bash "$ROOT/scripts/deploy_qwen_gpu_ecs.sh"

echo "==> GPU judge should be warm. Smoke: curl vLLM health on task (see ECS logs) or run scripts/gpu_smoke.sh"
