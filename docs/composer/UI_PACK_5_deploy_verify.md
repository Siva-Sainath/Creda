# UI PACK 5 — Deploy + verification matrix

**Prerequisites:** UI PACK 0–4 complete and passing local smoke.  
**Target:** Live Amplify `d32sg54oqu2gcb` branch `main`  
**Build meta:** `baseten-20260919-v65-ui-rewrite`

---

## Global deploy rules

- API URL: `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`
- `app.js` line 4 already hardcodes `API_URL` — no sed required unless you use `__CREDA_API_URL__` placeholder.
- AWS: `export AWS_PROFILE=creda-dev AWS_DEFAULT_REGION=ap-south-1`
- No PR.

---

## Step 1 — Confirm build meta

```bash
grep 'creda-build' /Users/siva/Documents/first_commit_hack/frontend/index.html
```

Must show: `baseten-20260919-v65-ui-rewrite`

---

## Step 2 — Build dist bundle

```bash
cd /Users/siva/Documents/first_commit_hack/frontend
rm -rf dist deploy.zip
mkdir -p dist
cp index.html styles.css app.js dist/
cd dist && zip -qr ../deploy.zip . && cd ..
ls -la deploy.zip
```

Zip must contain exactly: `index.html`, `styles.css`, `app.js` at archive root.

---

## Step 3 — Amplify deployment

```bash
export AWS_PROFILE=creda-dev
export AWS_DEFAULT_REGION=ap-south-1
APP_ID=d32sg54oqu2gcb
BRANCH=main

DEPLOY=$(aws amplify create-deployment \
  --app-id "$APP_ID" \
  --branch-name "$BRANCH" \
  --output json)

JOB=$(echo "$DEPLOY" | jq -r .jobId)
URL=$(echo "$DEPLOY" | jq -r .zipUploadUrl)

echo "Job: $JOB"
curl -sf -X PUT -T deploy.zip -H "Content-Type: application/zip" "$URL"

aws amplify start-deployment \
  --app-id "$APP_ID" \
  --branch-name "$BRANCH" \
  --job-id "$JOB"

# Wait for SUCCEED (poll every 15s)
while true; do
  STATUS=$(aws amplify get-job --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB" \
    --query 'job.summary.status' --output text)
  echo "Status: $STATUS"
  [ "$STATUS" = "SUCCEED" ] && break
  [ "$STATUS" = "FAILED" ] && exit 1
  sleep 15
done
```

---

## Step 4 — Live meta check

```bash
curl -sL https://main.d32sg54oqu2gcb.amplifyapp.com/ | grep -o 'creda-build" content="[^"]*"'
```

**Pass:** `baseten-20260919-v65-ui-rewrite`

Hard-refresh browser (Cmd+Shift+R) before visual tests.

---

## Step 5 — Commit deploy artifacts (optional but recommended)

```bash
cd /Users/siva/Documents/first_commit_hack
git add frontend/index.html frontend/styles.css frontend/app.js docs/composer/
git commit -m "$(cat <<'EOF'
feat(ui): v65 full rewrite — mobile-first layout, P0 fixes, wait vectors

Single-layer CSS, judgment-host in flow, follow-up grace window,
stamp-gated wait storyboard, 1.4s scene dwell. Composer packs in docs/composer/.
EOF
)"
```

Do not commit `deploy.zip` unless repo already tracks it.

---

## Verification matrix UI-T1 – UI-T12

Run at viewports: **390**, **768**, **1024**, **1440**, **1920** (IDE browser or DevTools device mode). Screenshot failures.

| ID | Test | Pass criteria | Fail if |
|----|------|---------------|---------|
| **UI-T1** | Horizontal scroll | No horizontal scrollbar at any width | Any `overflow-x` scroll |
| **UI-T2** | Mobile scroll | At 390px, document scrolls top-to-footer | Content clipped, cannot reach follow-up |
| **UI-T3** | Mobile overlap | Toolbar, safety line, stamp, tiles, follow-up do not overlap | Any text/button obscured |
| **UI-T4** | Desktop bleed | At 1440/1920, panes use width; no ~720px column | Dead gutters >200px each side |
| **UI-T5** | Wait scenes | Fee-scam case: 5 distinct scenes, each ≥1.4s | Flash <1s; stamp before ready |
| **UI-T6** | Reveal opacity | After result: `getComputedStyle(el).opacity === "1"` on stamp, headline, all `.tactic-tile` | Any <1 |
| **UI-T7** | Check another | Click `#btn-new` immediately after stamp | Blocked or requires multiple clicks |
| **UI-T8** | Follow-up | Ask "Is amaz0n-jobs.in a real Amazon domain?" | Board/headline/tiles change; hangs >15s with no answer |
| **UI-T9** | Repeat cases | 3 consecutive Checks | Ghost opacity on 2nd/3rd |
| **UI-T10** | Banned CSS | `grep` banned selectors in styles.css | Any match >0 |
| **UI-T11** | Console clean | DevTools console during full flow | Errors from missing DOM |
| **UI-T12** | Reduced motion | `prefers-reduced-motion: reduce` | Board visible, no stuck animation |

### UI-T10 grep script

```bash
cd /Users/siva/Documents/first_commit_hack/frontend
for s in flip-card bento telegram-band demo-chip creda-v58 "max-width: 720px"; do
  n=$(grep -c "$s" styles.css 2>/dev/null || echo 0)
  echo "$s: $n"
  [ "$n" != "0" ] && exit 1
done
echo "UI-T10 PASS"
```

### UI-T6 DevTools snippet (run on result view)

```javascript
[".board-stamp", "#board-headline", ".tactic-tile"].forEach(sel => {
  document.querySelectorAll(sel).forEach(el => {
    const o = getComputedStyle(el).opacity;
    if (o !== "1") console.error("BAD", sel, o, el);
  });
});
```

### UI-T8 test paste (fee scam)

```
Congratulations! Amazon is hiring remote workers.
Pay INR 5000 registration fee to amaz0n-jobs.in via UPI.
Reply with OTP to confirm.
```

---

## API smoke (optional, same session)

```bash
export CREDA_API_URL=https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
curl -s "$CREDA_API_URL/health" | jq '.dataReady, .judgeMode'
```

---

## Go / no-go for demo

| Green (ship) | Red (do not demo) |
|--------------|-------------------|
| UI-T1–T4, T6–T9 pass | Any P0 fail |
| UI-T5 pass or honest slow CPU wait | Stamp before verdict |
| UI-T8 answer or 8s deferral | Follow-up wipes board |
| Meta v65 live | Old v64 meta after hard refresh |

**Out of scope (do not claim):** Telegram photo VLM, screenshot upload, sub-30s Check on CPU path.

---

## Rollback

```bash
git log --oneline -5
git revert HEAD   # or checkout pre-v65 commit for frontend/ only
# redeploy previous deploy.zip
```
