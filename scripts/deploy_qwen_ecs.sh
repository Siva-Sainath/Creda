#!/usr/bin/env bash
# Build judge worker image, push to ECR, deploy ECS (SageMaker VLM backend by default).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${AWS_PROFILE:-creda-dev}"
REGION="${AWS_REGION:-ap-south-1}"
STACK_MAIN="${CREDA_STACK:-creda-mumbai}"
STACK_ECS="${CREDA_QWEN_STACK:-creda-qwen-ecs}"
WORKER_REPO="${CREDA_QWEN_REPO:-creda-qwen-worker}"
IMAGE_TAG="${CREDA_QWEN_TAG:-$(date +%Y%m%d%H%M%S)}"
JUDGE_BACKEND="${CREDA_JUDGE_BACKEND:-llama}"
SAGEMAKER_ENDPOINT="${CREDA_SM_ENDPOINT:-creda-qwen-judge}"
LLAMA_REPO="${CREDA_LLAMA_REPO:-creda-qwen-llama}"
LLAMA_TAG="${CREDA_LLAMA_TAG:-creda-20260918194859}"

aws_cli() { aws --profile "$PROFILE" --region "$REGION" "$@"; }

echo "==> Resolve creda-mumbai outputs"
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
LLAMA_URI="${ECR_HOST}/${LLAMA_REPO}:${LLAMA_TAG}"

ensure_repo() {
  aws_cli ecr describe-repositories --repository-names "$1" >/dev/null 2>&1 || \
    aws_cli ecr create-repository --repository-name "$1" --image-tag-mutability IMMUTABLE \
      --image-scanning-configuration scanOnPush=true >/dev/null
}

echo "==> Ensure ECR repository exists"
ensure_repo "$WORKER_REPO"

echo "==> Docker login"
aws_cli ecr get-login-password | docker login --username AWS --password-stdin "$ECR_HOST"

echo "==> Build and push judge worker image"
docker build --platform linux/amd64 -t "$WORKER_URI" "$ROOT/infra/qwen-ecs"
docker push "$WORKER_URI"

echo "==> Deploy ECS stack ($STACK_ECS) backend=$JUDGE_BACKEND endpoint=$SAGEMAKER_ENDPOINT"
aws_cli cloudformation deploy \
  --template-file "$ROOT/infra/qwen-ecs/template.yaml" \
  --stack-name "$STACK_ECS" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    "ImageUri=${WORKER_URI}" \
    "CasesTableName=${CASES_TABLE}" \
    "EvidenceBucketName=${EVIDENCE_BUCKET}" \
    "SageMakerEndpointName=${SAGEMAKER_ENDPOINT}" \
    "JudgeBackend=${JUDGE_BACKEND}" \
    "LlamaImageUri=${LLAMA_URI}" \
    "QwenQueueUrl=${QWEN_QUEUE_URL}" \
    "QwenQueueArn=${QWEN_QUEUE_ARN}" \
    "VpcId=${VPC_ID}" \
    "SubnetIds=${SUBNET_IDS}"

echo ""
echo "Deploy complete."
echo "  Worker image:     $WORKER_URI"
echo "  Judge backend:    $JUDGE_BACKEND"
echo "  SM endpoint:      $SAGEMAKER_ENDPOINT"
echo "  Cluster/service:  creda-qwen-cpu"
