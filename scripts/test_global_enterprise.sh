#!/usr/bin/env bash
set -euo pipefail
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
MSG='From: +1 (555) 019-2834 / HR Dept - Global Enterprise Solutions Ltd.

Subject: Urgent Hiring: Remote Operations Assistant (Part-Time/Full-Time)

Dear Candidate,

Congratulations! Your resume has been shortlisted by our automated screening system on LinkedIn for the position of Remote Data Entry & Operations Assistant at Global Enterprise Solutions Ltd.

Job Details:

• Working Hours: Flexible (1–2 hours per day)
• Pay Rate: $75 – $120 / hour (Paid daily via wire transfer, Crypto, or Check)
• Location: 100% Remote / Work from Home

Due to high volume, we are conducting interviews exclusively via Telegram / WhatsApp. To secure your position and receive your official offer letter along with a $2,500 equipment allowance check, please contact our hiring director Dr. Arthur Vance immediately.

Telegram Username: @ArthurVance_HR_Global

Best regards,
Recruitment Team
Global Enterprise Solutions Ltd.'

R=$(curl -s -X POST "$API/cases" -H 'Content-Type: application/json' -d "$(jq -n --arg t "$MSG" '{offerText:$t,employerHint:"Global Enterprise Solutions Ltd",locale:"en-US"}')")
echo "$R" | jq .
CID=$(echo "$R" | jq -r .caseId)
TOK=$(echo "$R" | jq -r .accessToken)
for i in $(seq 1 80); do
  sleep 2
  D=$(curl -s -H "X-Case-Token: $TOK" "$API/cases/$CID")
  if [[ "$(echo "$D" | jq -r .status)" == "COMPLETED" && "$(echo "$D" | jq -r .agentStatus)" == "READY" && "$(echo "$D" | jq -r .verdict)" != "pending" ]]; then
    echo "$D" | jq '{verdict,headline,agentSource,pipelineLog,reasoning:.agentReasoning,tactics:(.matchedTactics|length)}'
    exit 0
  fi
done
echo "TIMEOUT"
exit 1
