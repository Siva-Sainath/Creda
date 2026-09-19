#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/bin:${PATH:-}"
PROFILE="${AWS_PROFILE:-creda-dev}"
REGION="${AWS_REGION:-ap-south-1}"
VENV="/tmp/creda-sm-venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q 'botocore[crt]' 'boto3' 'sagemaker>=2.232.0,<3.0.0'
fi
export AWS_PROFILE="$PROFILE" AWS_REGION="$REGION"
ARGS=()
if [[ "${CREDA_SM_FORCE:-}" == "1" ]]; then ARGS+=(--force); fi
"$VENV/bin/python" /Users/siva/Documents/first_commit_hack/infra/sagemaker/deploy_judge_endpoint.py "${ARGS[@]}" "$@"
