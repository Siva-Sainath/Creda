```
COMPOSER 2.5 | Phase 4: Telegram + Amplify deploy + smoke

Branch: creda/mvp-g4dn-ship
Modes: /architect then /poteto-mode
No GitHub PR unless the human explicitly asks.
SageMaker: stay deleted.
Live UI: https://main.d32sg54oqu2gcb.amplifyapp.com
Live API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
Notion playbook: https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd
Telegram docs: docs/TELEGRAM_SETUP.md
```

## Branch guard (run first)

```bash
cd /Users/siva/Documents/first_commit_hack
git branch --show-current    # must print creda/mvp-g4dn-ship
git status -sb
bash scripts/smoke_mvp.sh      # baseline before deploy
```

Phases 1 through 3 must be complete before this pack.

## Goal

Telegram onboarding CTA (<=3 steps). Amplify deploy with all frontend files. Create and run `scripts/verify_full_loop.sh`. Demo-ready only when verify exits 0.

## Real file paths

| Area | Paths |
|------|-------|
| Frontend deploy | `frontend/amplify.yml`, `scripts/deploy_all.sh`, `frontend/dist/` |
| Telegram | `scripts/deploy_telegram.sh`, `scripts/setup_telegram_webhook.sh`, `scripts/test_telegram_webhook.sh`, `docs/TELEGRAM_SETUP.md` |
| Verify (new) | `scripts/verify_full_loop.sh` |
| Existing tests | `scripts/smoke_mvp.sh`, `scripts/run_test_catalog.sh`, `scripts/test_injection_fixtures.sh`, `scripts/test_followup.sh`, `scripts/test_ui_journey.mjs`, `scripts/test_e2e_full.sh` |
| Fixtures | `scripts/fixtures/ocr_scam_offer.png`, `scripts/test_cases.json` |
| GPU | `scripts/creda_gpu_up.sh`, `scripts/creda_gpu_down.sh` |

## Step 1: Telegram onboarding CTA

In `frontend/index.html` and `frontend/app.js`:

- Compact chip linking to `https://t.me/CredashieldBot`
- Intake trust row and result aftercare placement (not a giant banner)
- Onboarding copy in <=3 steps:
  1. Open @CredashieldBot
  2. Send /start
  3. Paste offer or forward message

Reference `docs/TELEGRAM_SETUP.md` for webhook setup.

Deploy Telegram Lambdas if not present:

```bash
bash scripts/deploy_telegram.sh
bash scripts/setup_telegram_webhook.sh
bash scripts/test_telegram_webhook.sh
```

Skip webhook test with logged reason if bot token not configured locally.

## Step 2: Amplify deploy

Build dist with API URL injection:

```bash
export CREDA_API_URL=https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
export AWS_PROFILE=creda-dev

mkdir -p frontend/dist
cp frontend/index.html frontend/dist/
cp frontend/styles.css frontend/dist/
cp frontend/motion.js frontend/dist/
sed "s|__CREDA_API_URL__|${CREDA_API_URL}|g" frontend/app.js > frontend/dist/app.js
```

Upload via Amplify console or `scripts/deploy_all.sh` frontend section.

Confirm live UI at https://main.d32sg54oqu2gcb.amplifyapp.com reflects the build tag in `<meta name="creda-build">`.

## Step 3: Create verify_full_loop.sh

Create `scripts/verify_full_loop.sh` per the spec in `docs/astra/CREDA_ASTRA_COMPOSER_PLAN.md`.

Script structure:

```bash
#!/usr/bin/env bash
set -euo pipefail
export AWS_PROFILE="${AWS_PROFILE:-creda-dev}"
export CREDA_API_URL="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
export CREDA_UI_URL="${CREDA_UI_URL:-https://main.d32sg54oqu2gcb.amplifyapp.com}"
export CREDA_TEST_STRICT=true

echo "==> 1. API health"
curl -sf "$CREDA_API_URL/health" | jq -e '.ok == true'

echo "==> 2. SageMaker endpoint count"
test "$(aws sagemaker list-endpoints --region ap-south-1 --query 'length(Endpoints)' --output text)" = "0"

echo "==> 3. smoke_mvp"
bash scripts/smoke_mvp.sh

echo "==> 4. test catalog strict"
CREDA_TEST_STRICT=true bash scripts/run_test_catalog.sh

echo "==> 5. injection fixtures"
bash scripts/test_injection_fixtures.sh

echo "==> 6. follow-up snapshot"
bash scripts/test_followup.sh   # extend to assert ruling unchanged + ev_search_*

echo "==> 7. multimodal fixture"
# create case with scripts/fixtures/ocr_scam_offer.png, assert agentSource vllm

echo "==> 8. telegram webhook"
bash scripts/test_telegram_webhook.sh || echo "SKIP: telegram not deployed"

echo "==> 9. UI journey 1440 + 390"
# extend test_ui_journey.mjs for both viewports

echo "==> 10. no three.js in dist"
! grep -qi 'three' frontend/dist/index.html

echo "==> COST: g4dn \$0.579/hr, ~\$14.7/day, ~16 days on \$238"
```

Make executable: `chmod +x scripts/verify_full_loop.sh`

## Step 4: Extend test_followup.sh

Add assertions after follow-up "Is the careers link real?":

- GET case: `verdict` and `headline` match pre-follow-up values
- Response or presentation includes exhibit id matching `ev_search_*`
- `nextActions` array non-empty

## Step 5: Extend test_ui_journey.mjs

Add viewport runs:

- 1440 x 900 desktop
- 390 x 844 mobile

Assertions:

- No `creda://` in page content
- `#ruling-host` text identical before and after follow-up click
- Next steps list has at least one item with non-empty text
- Exhibit title texts are unique
- Follow-up dock `position` is `sticky` or `fixed` on mobile
- No `document.documentElement.scrollWidth > window.innerWidth`

## Step 6: Run full verify

```bash
bash scripts/verify_full_loop.sh
```

Fix failures in order. Re-run until green.

## Step 7: GPU down optional

After verify passes, operator may scale down to save credits:

```bash
bash scripts/creda_gpu_down.sh
```

Document that demo judging windows should run `creda_gpu_up.sh` first.

## Do

- Add compact Telegram CTA with <=3 step copy
- Deploy all four frontend files to Amplify
- Create `scripts/verify_full_loop.sh`
- Extend follow-up and UI journey tests
- Print cost line on verify success
- Run verify before declaring demo-ready

## Do not

- Open a GitHub PR
- Recreate SageMaker
- Skip verify and claim SHIP
- Deploy frontend without API URL sed
- Leave Telegram as t.me link only with no onboarding copy

## Acceptance

- [ ] Telegram CTA visible on intake and result aftercare
- [ ] Onboarding copy <=3 steps
- [ ] Amplify live UI matches local dist build tag
- [ ] `scripts/verify_full_loop.sh` exists and is executable
- [ ] Verify script passes green end-to-end
- [ ] SageMaker endpoint count = 0 asserted in verify
- [ ] Multimodal fixture reaches vllm or creda-vlm agentSource
- [ ] Follow-up test asserts ruling unchanged and ev_search exhibit
- [ ] UI journey passes at 1440 px and 390 px
- [ ] No `three` script in built page
- [ ] Cost line printed: g4dn $0.579/hr, ~$14.7/day, ~16 days on $238
- [ ] No GitHub PR opened
