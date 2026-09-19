#!/usr/bin/env bash
# Build worker image + deploy GPU ECS stack (g4dn.xlarge + vLLM). See DEPLOY.md for $/hr.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${AWS_PROFILE:-creda-dev}"
REGION="${AWS_REGION:-ap-south-1}"
STACK_MAIN="${CREDA_STACK:-creda-mumbai}"
STACK_GPU="${CREDA_GPU_STACK:-creda-qwen-gpu}"
WORKER_REPO="${CREDA_QWEN_REPO:-creda-qwen-worker}"
IMAGE_TAG="${CREDA_QWEN_TAG:-gpu-$(date +%Y%m%d%H%M%S)}"
JUDGE_BACKEND="${CREDA_JUDGE_BACKEND:-vllm}"
VLLM_MODEL="${CREDA_VLLM_MODEL:-Qwen/Qwen3-VL-4B-Instruct}"

aws_cli() { aws --profile "$PROFILE" --region "$REGION" "$@"; }

CASES_TABLE=$(aws_cli cloudformation describe-stacks --stack-name "$STACK_MAIN" \
  --query "Stacks[0].Outputs[?OutputKey=='CasesTableName'].OutputValue" --output text)
EVIDENCE_BUCKET=$(aws_cli cloudformation describe-stacks --stack-name "$STACK_MAIN" \
  --query "Stacks[0].Outputs[?OutputKey=='EvidenceBucketName'].OutputValue" --output text)
QWEN_QUEUE_URL=$(aws_cli cloudformation describe-stacks --stack-name "$STACK_MAIN" \
  --query "Stacks[0].Outputs[?OutputKey=='QwenQueueUrl'].OutputValue" --output text)
QWEN_QUEUE_ARN=$(aws_cli cloudformation describe-stacks --stack-name "$STACK_MAIN" \
  --query "Stacks[0].Outputs[?OutputKey=='QwenQueueArn'].OutputValue" --output text)
VPC_ID=$(aws_cli ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SUBNET_IDS=$(aws_cli ec2 describe-subnets --filters Name=default-for-az,Values=true \
  --query 'Subnets[0:2].SubnetId' --output text | tr '\t' ',')
ACCOUNT=$(aws_cli sts get-caller-identity --query Account --output text)
ECR_HOST="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
WORKER_URI="${ECR_HOST}/${WORKER_REPO}:${IMAGE_TAG}"

aws_cli ecr describe-repositories --repository-names "$WORKER_REPO" >/dev/null 2>&1 || \
  aws_cli ecr create-repository --repository-name "$WORKER_REPO" --image-tag-mutability IMMUTABLE >/dev/null

aws_cli ecr get-login-password | docker login --username AWS --password-stdin "$ECR_HOST"
docker build --platform linux/amd64 -t "$WORKER_URI" "$ROOT/infra/qwen-ecs"
docker push "$WORKER_URI"

aws_cli cloudformation deploy \
  --template-file "$ROOT/infra/qwen-ecs/template-gpu.yaml" \
  --stack-name "$STACK_GPU" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "WorkerImageUri=${WORKER_URI}" \
    "CasesTableName=${CASES_TABLE}" \
    "EvidenceBucketName=${EVIDENCE_BUCKET}" \
    "QwenQueueUrl=${QWEN_QUEUE_URL}" \
    "QwenQueueArn=${QWEN_QUEUE_ARN}" \
    "VpcId=${VPC_ID}" \
    "SubnetIds=${SUBNET_IDS}" \
    "VllmModel=${VLLM_MODEL}" \
    "JudgeBackend=${JUDGE_BACKEND}"

echo "GPU stack deployed: $STACK_GPU worker=$WORKER_URI backend=$JUDGE_BACKEND (~\$0.579/hr g4dn.xlarge)"
