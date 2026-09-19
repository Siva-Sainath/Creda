#!/usr/bin/env bash
# Scale GPU ASG to 0 to stop g4dn billing. Fargate llama fallback remains for text-only.
set -euo pipefail
PROFILE="${AWS_PROFILE:-creda-dev}"
REGION="${AWS_REGION:-ap-south-1}"
STACK="${CREDA_GPU_STACK:-creda-qwen-gpu}"

ASG=$(aws cloudformation describe-stack-resources --stack-name "$STACK" --profile "$PROFILE" --region "$REGION" \
  --query "StackResources[?ResourceType=='AWS::AutoScaling::AutoScalingGroup'].PhysicalResourceId" --output text 2>/dev/null || true)
if [[ -z "$ASG" || "$ASG" == "None" ]]; then
  echo "No GPU ASG found for stack $STACK"
  exit 1
fi
aws autoscaling update-auto-scaling-group --auto-scaling-group-name "$ASG" --desired-capacity 0 \
  --profile "$PROFILE" --region "$REGION"
echo "Scaled $ASG to desired=0. Fargate text fallback: creda-qwen-cpu (llama)"
