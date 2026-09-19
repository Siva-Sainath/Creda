# Grok end-product checklist — ship Creda as a finished demo

**Audience:** Grok (UI polish + copy) + operator (deploy)  
**Live:** https://main.d32sg54oqu2gcb.amplifyapp.com  
**API:** https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com  
**Test catalog:** `scripts/test_cases.json` + `bash scripts/run_test_catalog.sh`

---

## What “done” means

A judge-ready product link where a stranger can:

1. Paste a real recruitment message (or upload a screenshot).
2. See useful progress within **10 seconds** (evidence timeline while judge runs).
3. Get a **verdict + reasoning + actions** in under **~2 minutes** on CPU ECS.
4. Ask **follow-up questions** and get concise answers grounded in evidence.
5. **Report a missed scam** in one tap from the result screen.

No demo chips. No hardcoded verdicts. No SageMaker burn.

---

## Already shipped (do not re-build)

| Area | Status |
|------|--------|
| ECS-primary judge (`JUDGE_BACKEND=llama`) | Done — SageMaker endpoint removed |
| Baseten visual rewrite (build `baseten-20260919-53`) | Done in `frontend/index.html` |
| Blank ruling stamp fix (`stamp-fill` / `stamp-text`) | Done |
| Vector tactic tiles (not text walls) | Done |
| Add links intake (no Fee/Clean/Vague demo chips) | Done |
| Forum/advisory ingest (6 sources, daily schedule) | Done — `forumIngestion: true` |
| ATS pipeline (17 sources, 47 employers) | Done |
| Link signals (Google Form, bit.ly, Telegram) | Done |
| Report missed scam + prefill | Done |
| PDF/image upload + CORS | Done |
| Follow-up API + UI | Done |
| Regression catalog (21 prompts + follow-ups) | Done — `scripts/test_cases.json` |

---

## Grok polish scope (finish the product feel)

From `docs/HANDOFF-GROK-UI.md` — **only these remain for “end product”**:

### P0 — Wait experience (users bail here)

- [x] Show **evidence timeline** as soon as `status=COMPLETED` even when `verdict=pending` (`live-exhibits` panel on wait view).
- [x] **Elapsed timer** on wait view (`#elapsed-timer`).
- [x] Stage copy tied to real **pipeline log** lines (`#wait-pipeline` + `#wait-subtitle`).
- [x] Honest copy when slow (“writing your ruling…”) — never blank.

### P1 — Result screen hierarchy

Top → bottom (mobile-first):

1. Verdict stamp + headline  
2. Agent reasoning (collapsible `<details>` — “Why Creda ruled this way”)  
3. Safe actions — **sticky “Do not pay”** on `high_risk` mobile (`#sticky-urgent`)  
4. Tactic tiles (vector grid)  
5. Evidence highlights (flip cards, tier pills)  
6. Uncertainty / still unknown  
7. Follow-up chips → prefill textarea  
8. Report a missed scam (result aftercare)

### P2 — Copy & trust

- [x] Footer: **“Creda explains its judgment from approved evidence…”**
- [x] Intake lede: “Deep checks can take up to two minutes.”
- Tier literacy: T1/T2 pills visible; never let T3 forum intel alone say “confirmed scam”.
- Honest gaps: “We could not verify the sender” beats false confidence.

### P3 — Mobile

- Single-column evidence grid (existing bento)  
- [x] Collapsible agent reasoning on mobile  
- [x] Sticky urgent action on high risk (mobile)  
- Composer + links panel usable at 375px width  

### P4 — Do NOT build (scope guard)

- No WebSocket  
- No client-side LLM  
- No new `agentPresentation` block types without backend schema change  
- No demo chip shortcuts in composer  

---

## Operator deploy checklist (one-time before calling it “end product”)

```bash
# 1. Backend health
curl -s https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com/health | jq '.status,.judgeMode,.searcher'

# 2. Frontend (bake API URL, zip, Amplify)
cd frontend
sed 's|__CREDA_API_URL__|https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com|g' index.html > dist/index.html
# amplify create-deployment → upload zip → start-deployment

# 3. Smoke (pick 3 from catalog — not the same 3 every time)
bash scripts/run_test_catalog.sh   # or manual from docs/TEST_PROMPTS.md

# 4. Hard-refresh note for judges
# Chrome: Cmd+Shift+R — confirm meta creda-build=baseten-20260919-53
```

### Optional (post-MVP)

- Custom domain on Amplify (Route53)  
- Telegram bot (`scripts/deploy_telegram.sh` — needs BotFather token)  
- GPU burst for demo hours only (not required for ship)  

---

## Grok test loop (manual, 15 minutes)

Use **different** prompts each run — full list in `docs/TEST_PROMPTS.md`.

| # | Type | Expect |
|---|------|--------|
| 1 | India fee scam (TCS/Flipkart/Infosys) | `high_risk`, fee exhibit, follow-up answers “no UPI before joining” |
| 2 | Legit ATS link (Anthropic/Figma/Coinbase GH URL) | vacancy exhibit; verdict `unverified` or `no_conflict_found` |
| 3 | Google Form + bit.ly enroll | link exhibits; likely `high_risk` |
| 4 | Vague LinkedIn DM | `unverified`, follow-up chips useful |
| 5 | Screenshot upload (`scripts/fixtures/ocr_scam_offer.png`) | OCR in pipeline log |
| 6 | Report missed scam from result | receipt / “Report sent” |
| 7 | Short input `hi` | inline error, no case |

**Pass:** Every case returns within ~2 min, stamp visible, follow-up works, no `fallback` badge.

---

## Known honest limitations (document in UI or FAQ, don’t hide)

| Limitation | User-facing line |
|------------|------------------|
| CPU judge 30–120s | “Deep checks can take up to two minutes.” |
| No LinkedIn/Indeed scrape | “We check official employer boards, not social DMs.” |
| Typosquat domains may stay `unverified` | “We flag suspicious links; always verify on the employer’s site.” |
| Tab-only case token | “Save your link — rulings stay in this browser tab.” |

---

## Priority order for Grok

1. **Wait screen** — evidence early + timer (biggest perceived quality jump)  
2. **Result hierarchy** — sticky “Do not pay”, collapse noise  
3. **Mobile pass** — 375px layout  
4. **Copy pass** — trust language, no model jargon  
5. **Deploy** — bump `creda-build` meta, Amplify job, hard-refresh verify  

When P0–P4 are checked and one Grok test loop passes → **call it end product**.
