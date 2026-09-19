#!/usr/bin/env bash
set -euo pipefail
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"

echo "=== Create base case ==="
R=$(curl -s -X POST "$API/cases" -H 'Content-Type: application/json' -d '{"offerText":"Congratulations! Amazon is hiring. Pay INR 3500 registration fee to hr.recruitment@gmail.com via UPI.","senderEmail":"hr.recruitment@gmail.com","employerHint":"Amazon"}')
CID=$(echo "$R" | jq -r .caseId)
TOK=$(echo "$R" | jq -r .accessToken)
echo "caseId=$CID"

wait_ready() {
  for i in $(seq 1 80); do
    sleep 2
    D=$(curl -s -H "X-Case-Token: $TOK" "$API/cases/$CID")
    ST=$(echo "$D" | jq -r .status)
    AS=$(echo "$D" | jq -r .agentStatus)
    V=$(echo "$D" | jq -r .verdict)
    if [[ "$ST" == "COMPLETED" && "$AS" == "READY" && "$V" != "pending" && -n "$V" ]]; then
      echo "$D" | jq '{verdict,agentSource,turns:(.conversationTurns|length)}'
      return 0
    fi
  done
  echo "TIMEOUT waiting for initial judgment"
  exit 1
}
wait_ready

echo "=== Free-form follow-up question ==="
curl -s -X POST "$API/cases/$CID/followup" -H 'Content-Type: application/json' -H "X-Case-Token: $TOK" \
  -d '{"answerText":"Why is this marked high risk if I only got it on Gmail?"}' | jq .

for i in $(seq 1 80); do
  sleep 2
  D=$(curl -s -H "X-Case-Token: $TOK" "$API/cases/$CID")
  ST=$(echo "$D" | jq -r .status)
  AS=$(echo "$D" | jq -r .agentStatus)
  V=$(echo "$D" | jq -r .verdict)
  if [[ "$ST" == "COMPLETED" && "$AS" == "READY" && "$V" != "pending" ]]; then
    echo "$D" | jq '{verdict,agentSource,reasoning:.agentReasoning,turns:.conversationTurns,stage}'
    TURNS=$(echo "$D" | jq '.conversationTurns|length')
    if [[ "$TURNS" -ge 1 ]]; then
      echo "PASS: follow-up loop completed with conversation turns"
      exit 0
    fi
    echo "FAIL: no conversation turns recorded"
    exit 1
  fi
done
echo "TIMEOUT on follow-up"
exit 1
