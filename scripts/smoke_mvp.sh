#!/usr/bin/env bash
set -euo pipefail
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
LABEL="${1:-case}"
BODY="${2:?body json required}"

echo "=== $LABEL ==="
R=$(curl -s -X POST "$API/cases" -H 'Content-Type: application/json' -d "$BODY")
CID=$(echo "$R" | jq -r .caseId)
TOK=$(echo "$R" | jq -r .accessToken)
echo "caseId=$CID"
START=$(date +%s)
for i in $(seq 1 80); do
  sleep 2
  D=$(curl -s -H "X-Case-Token: $TOK" "$API/cases/$CID")
  V=$(echo "$D" | jq -r '.verdict // empty')
  AS=$(echo "$D" | jq -r '.agentStatus // empty')
  SRC=$(echo "$D" | jq -r '.agentSource // empty')
  ST=$(echo "$D" | jq -r '.status // empty')
  if [[ "$ST" == "COMPLETED" && "$AS" == "READY" && -n "$V" && "$V" != "pending" ]]; then
    END=$(date +%s)
    ELAPSED=$((END - START))
    echo "$D" | jq --argjson elapsed "$ELAPSED" '{verdict,agentStatus,agentSource,headline,blocks:(.agentPresentation.blocks|length),reasoning:.agentReasoning,elapsed:$elapsed}'
    exit 0
  fi
  printf "  poll %s status=%s verdict=%s agent=%s source=%s\n" "$i" "$ST" "${V:-pending}" "$AS" "$SRC"
done
echo "TIMEOUT after 160s"
exit 1
