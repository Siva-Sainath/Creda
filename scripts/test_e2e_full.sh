#!/usr/bin/env bash
set -euo pipefail
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
FAIL=0

poll_case() {
  local cid="$1" tok="$2" label="$3"
  for _ in $(seq 1 70); do
    sleep 2
    local d
    d=$(curl -sf -H "X-Case-Token: $tok" "$API/cases/$cid")
    local st as v
    st=$(echo "$d" | jq -r .status)
    as=$(echo "$d" | jq -r .agentStatus)
    v=$(echo "$d" | jq -r .verdict)
    if [[ "$st" == "FAILED" ]]; then
      echo "FAIL $label: case FAILED $(echo "$d" | jq -r '.userMessage // .stage // .status')"
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

assert_field() {
  local label="$1" json="$2" field="$3" expect="$4"
  local got
  got=$(echo "$json" | jq -r "$field")
  if [[ "$got" != "$expect" ]]; then
    echo "FAIL $label: expected $field=$expect got $got"
    FAIL=1
    return 1
  fi
  echo "PASS $label: $field=$got"
}

echo "==> health"
curl -sf "$API/health" | jq -e '.status=="ok"' >/dev/null

echo "==> bad input returns nextAction"
BAD=$(curl -s -X POST "$API/cases" -H 'Content-Type: application/json' -d '{"offerText":"short"}')
echo "$BAD" | jq -e '.nextAction' >/dev/null || { echo "FAIL bad input missing nextAction"; FAIL=1; }

echo "==> full prompt catalog (replaces legacy Amazon/Stripe/Global Enterprise-only e2e)"
CREDA_API_URL="$API" bash /Users/siva/Documents/first_commit_hack/scripts/run_test_catalog.sh || FAIL=1

echo "==> vacancy identity (local)"
/Users/siva/Documents/first_commit_hack/scripts/test_vacancy_identity.sh || FAIL=1
/Users/siva/Documents/first_commit_hack/scripts/test_vacancy_evidence.sh || FAIL=1

if [[ "$FAIL" -eq 0 ]]; then
  echo "ALL E2E CHECKS PASSED"
  exit 0
fi
echo "SOME CHECKS FAILED"
exit 1
