#!/usr/bin/env bash
# Production prompt matrix — real user messages, no demo shortcuts.
set -euo pipefail
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
FAIL=0

poll_case() {
  local cid="$1" tok="$2" label="$3"
  for _ in $(seq 1 70); do
    sleep 2
    local d st as v
    d=$(curl -sf -H "X-Case-Token: $tok" "$API/cases/$cid")
    st=$(echo "$d" | jq -r .status)
    as=$(echo "$d" | jq -r .agentStatus)
    v=$(echo "$d" | jq -r .verdict)
    if [[ "$st" == "FAILED" ]]; then
      echo "FAIL $label: case FAILED"
      return 1
    fi
    if [[ "$st" == "COMPLETED" && "$as" == "READY" && "$v" != "pending" && "$v" != "null" ]]; then
      echo "$d"
      return 0
    fi
  done
  echo "FAIL $label: timeout"
  return 1
}

run_case() {
  local label="$1" payload="$2" expect_verdict="${3:-}"
  echo "==> $label"
  local r d v src reasoning
  r=$(curl -sf -X POST "$API/cases" -H 'Content-Type: application/json' -d "$payload")
  d=$(poll_case "$(echo "$r" | jq -r .caseId)" "$(echo "$r" | jq -r .accessToken)" "$label") || { FAIL=1; return; }
  v=$(echo "$d" | jq -r .verdict)
  src=$(echo "$d" | jq -r .agentSource)
  reasoning=$(echo "$d" | jq -r '.agentReasoning // ""' | head -c 80)
  echo "  verdict=$v agentSource=$src reasoning=${reasoning}..."
  if [[ -n "$expect_verdict" && "$v" != "$expect_verdict" ]]; then
    echo "  FAIL expected verdict $expect_verdict got $v"
    FAIL=1
  else
    echo "  PASS"
  fi
  if [[ "$src" != "creda" ]]; then
    echo "  FAIL agentSource not creda"
    FAIL=1
  fi
}

echo "==> health + judge"
curl -sf "$API/health" | jq -e '.status=="ok" and .judgeMode=="creda"' >/dev/null

run_case "whatsapp-protonmail" "$(jq -n --arg t 'Got this on WhatsApp: Remote data entry, 18 LPA. Send resume to hiring@protonmail.com. Start Monday.' '{offerText:$t,locale:"en-IN"}')" ""
run_case "amazon-deposit" "$(jq -n --arg t 'Amazon hiring. Pay INR 5000 security deposit to hr@amaz0n-jobs.in before onboarding.' '{offerText:$t,employerHint:"Amazon"}')" "high_risk"
run_case "stripe-official" "$(jq -n --arg t 'Stripe Software Engineer. Apply at https://stripe.com/jobs/search?gh_jid=8172510. No fees.' '{offerText:$t,employerHint:"Stripe",links:["https://stripe.com/jobs/search?gh_jid=8172510"]}')" ""

echo "==> follow-up reasoning"
R=$(curl -sf -X POST "$API/cases" -H 'Content-Type: application/json' -d '{"offerText":"Pay 3500 registration fee for Amazon job. hr.recruitment@gmail.com","employerHint":"Amazon"}')
CID=$(echo "$R" | jq -r .caseId)
TOK=$(echo "$R" | jq -r .accessToken)
poll_case "$CID" "$TOK" "followup-base" >/dev/null
curl -sf -X POST "$API/cases/$CID/followup" -H 'Content-Type: application/json' -H "X-Case-Token: $TOK" \
  -d '{"answerText":"Does Amazon ever ask for UPI payment before joining?"}' >/dev/null
D=$(poll_case "$CID" "$TOK" "followup-done")
TURNS=$(echo "$D" | jq '.conversationTurns|length')
[[ "$TURNS" -ge 1 ]] && echo "PASS follow-up turns=$TURNS" || { echo "FAIL follow-up turns"; FAIL=1; }

echo "==> short input rejected"
HTTP=$(curl -s -o /tmp/bad.json -w '%{http_code}' -X POST "$API/cases" -H 'Content-Type: application/json' -d '{"offerText":"hi"}')
[[ "$HTTP" == "400" ]] && jq -e '.nextAction' /tmp/bad.json >/dev/null && echo "PASS short input 400" || { echo "FAIL short input"; FAIL=1; }

if [[ "$FAIL" -eq 0 ]]; then echo "PROMPT MATRIX PASSED"; exit 0; fi
echo "PROMPT MATRIX FAILED"; exit 1
