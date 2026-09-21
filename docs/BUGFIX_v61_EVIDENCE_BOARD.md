# BUGFIX v61 — Evidence board (VT/HIBP/Baseten density)

**Date:** 2026-09-19 IST  
**Build:** `baseten-20260919-v61-evidence-board`  
**Base:** Live v60 fullscreen shell (no 720px postcard regress)

## Results grammar (locked)

1. Stamp first (solid HIGH RISK / etc.)
2. Headline ≤8 words
3. Optional one meta line (sender/domain)
4. **2–3 action chips immediately under stamp**
5. ≤6 flat tiles in **3×2**: icon + 2-word label + ONE fact; color = severity
6. Extra → `+N checks` collapse
7. No flip cards; no email body / full URLs / essays on canvas
8. Full viewport both panes

## Other fixes

- `extractRawActions` for empty `nextActions: []` → presentation `safe_actions`
- `consequenceFor` never copies headline (screen-reader / sticky)
- Follow-up preserves stamp/tiles/orders; blocks interim “writing the explanation”
- Wait playlist ≥700ms/scene + human scene copy
- Intake fold: Telegram + demos reachable; OTP warning clear of toolbar
- Stamp fill solid/high-contrast

## Files

`frontend/index.html`, `frontend/app.js`, `frontend/styles.css`, `frontend/dist/*`,  
`docs/CREDA_RESULTS_DASHBOARD_BRIEF.md`, `docs/BUGFIX_v61_EVIDENCE_BOARD.md`

## Local QA (2026-09-19 ~18:00 IST)

Screenshots under `/workspace/screenshots/`:
- `v61-both-panes.png` — intake left + VT/HIBP results right (mock HIGH RISK)
- `v61-results-mock.png` — same
- `v61-intake.png` — intake fold with Telegram + demo chips

Verified: no flip-card in DOM, 6 tiles 3×2, 3 action chips under stamp, headline ≤8 words, meta line, solid HIGH RISK stamp.

## Deploy status

`frontend/deploy.zip` ready (API URL baked). Amplify upload **blocked on this box**: profile `creda-dev` has no credentials (`aws login` required). Parent/Mac: run Amplify section of `scripts/deploy_all.sh` or:

```bash
cd frontend
API=https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
# dist already baked; or rebuild then:
DEPLOY=$(aws amplify create-deployment --app-id d32sg54oqu2gcb --branch-name main --region ap-south-1 --profile creda-dev --output json)
JOB=$(echo "$DEPLOY" | jq -r .jobId)
URL=$(echo "$DEPLOY" | jq -r .zipUploadUrl)
curl -s -X PUT -T deploy.zip -H "Content-Type: application/zip" "$URL"
aws amplify start-deployment --app-id d32sg54oqu2gcb --branch-name main --job-id "$JOB" --region ap-south-1 --profile creda-dev
```
