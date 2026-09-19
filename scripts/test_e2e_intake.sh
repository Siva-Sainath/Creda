#!/usr/bin/env bash
set -euo pipefail
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"

echo "==> health"
curl -sf "$API/health" | jq '{status,judgeMode,intakeChannels,multimodal}'

echo "==> upload-url"
UP=$(curl -sf -X POST "$API/upload-url" -H 'Content-Type: application/json' -d '{"contentType":"image/jpeg"}')
echo "$UP" | jq '{key,contentType,maxBytes,hasUrl:(.uploadUrl!=null)}'

echo "==> text case (Global Enterprise)"
MSG='From: +1 (555) 019-2834 / HR Dept - Global Enterprise Solutions Ltd.
Subject: Urgent Hiring: Remote Operations Assistant
Pay via wire transfer, Crypto, or Check. Interview on Telegram @ArthurVance_HR_Global
Equipment allowance check $2,500. Global Enterprise Solutions Ltd.'
R=$(curl -sf -X POST "$API/cases" -H 'Content-Type: application/json' -d "$(jq -n --arg t "$MSG" '{offerText:$t,sourceChannel:"web",locale:"en-US"}')")
CID=$(echo "$R" | jq -r .caseId)
TOK=$(echo "$R" | jq -r .accessToken)
echo "caseId=$CID"

for i in $(seq 1 60); do
  sleep 2
  D=$(curl -sf -H "X-Case-Token: $TOK" "$API/cases/$CID")
  if [[ "$(echo "$D" | jq -r .status)" == "COMPLETED" && "$(echo "$D" | jq -r .agentStatus)" == "READY" && "$(echo "$D" | jq -r .verdict)" != "pending" ]]; then
    echo "$D" | jq '{verdict,headline,sourceChannel:.sourceChannel,agentSource,pipelineLog}'
    exit 0
  fi
done
echo "TIMEOUT"
exit 1
