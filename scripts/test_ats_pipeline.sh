#!/usr/bin/env bash
set -euo pipefail
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"

poll_case() {
  local cid="$1" tok="$2"
  for _ in $(seq 1 60); do
    sleep 2
    local d
    d=$(curl -sf -H "X-Case-Token: $tok" "$API/cases/$cid")
    if [[ "$(echo "$d" | jq -r .status)" == "COMPLETED" && "$(echo "$d" | jq -r .agentStatus)" == "READY" && "$(echo "$d" | jq -r .verdict)" != "pending" ]]; then
      echo "$d"
      return 0
    fi
  done
  return 1
}

echo "==> Stripe + official Greenhouse link (ATS vacancy match)"
STRIPE_MSG='Stripe is hiring Software Engineer. Apply at https://stripe.com/jobs/search?gh_jid=8172510. No fees required.'
R=$(curl -sf -X POST "$API/cases" -H 'Content-Type: application/json' -d "$(jq -n --arg t "$STRIPE_MSG" '{offerText:$t,employerHint:"Stripe",links:["https://stripe.com/jobs/search?gh_jid=8172510"],locale:"en-US"}')")
CID=$(echo "$R" | jq -r .caseId)
TOK=$(echo "$R" | jq -r .accessToken)
D=$(poll_case "$CID" "$TOK") || { echo "TIMEOUT stripe"; exit 1; }
echo "$D" | jq '{verdict,headline,pipelineLog,atsEvidence:(.evidence|map(select(.check=="vacancy")))}'

echo "==> Global Enterprise scam (tactics)"
/Users/siva/Documents/first_commit_hack/scripts/test_global_enterprise.sh
