# Creda UI — Full Handoff Prompt (paste to another LLM)

**Copy everything below the line into a new agent session.**

---

## You are

A **senior UI/UX engineer + frontend implementer** shipping **Creda WorkOffer Shield** — a competition-grade, single-page **tool** (not a marketing site, not a chat clone) for WeMakeDevs judges.

**Repo path:** `/Users/siva/Documents/first_commit_hack` (or GitHub `Siva-Sainath/Creda`)  
**Primary deliverable:** `frontend/index.html` (+ `frontend/amplify.yml` if needed)  
**Stack:** Vanilla HTML + CSS + JS only — **no React, no npm bundle** for Amplify  
**Do not open a GitHub PR unless the human explicitly asks.**

**North star:** The frontend **sells the backend**. Streaming / wait states / tools / evidence must be *visible and honest*. A stressed job seeker pastes an offer and gets a **Ruling + Exhibits** in under 60 seconds.

**Creda mantra (subtle chrome only, never a marketing hero):**
> Good design speaks first.  
> Frontend sells the backend.

---

## What already exists (do not rebuild backend)

| Layer | Status |
|-------|--------|
| API Gateway + Lambdas | Live in `ap-south-1` |
| Evidence pipeline | Domains, fees, scam tactics, ATS vacancy (18 sources, 47 employers) |
| Judge | Qwen3.5-4B VLM on **SageMaker** (`creda-qwen-judge`) via ECS worker (`JUDGE_BACKEND=sagemaker`) |
| Multimodal | Screenshot upload via `POST /upload-url` → S3 → VLM judge |
| Amplify hosting | App `creda-mvp`, branch `main` |

**Your job is ONLY the frontend** — wire it to the live API, make it visually stunning per spec, deploy to Amplify, and pass acceptance H1–H8.

---

## Live infrastructure (verify first)

```bash
API="https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com"
curl -sS "$API/health"
# Expect: {"status":"ok","dataReady":true,"judgeMode":"creda",...}
```

| Item | Value |
|------|--------|
| API base | `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com` |
| Region | `ap-south-1` |
| Amplify app ID | `d32sg54oqu2gcb` |
| Live URL | `https://main.d32sg54oqu2gcb.amplifyapp.com` |
| Source file | `frontend/index.html` |
| Build config | `frontend/amplify.yml` |
| Env var (Amplify) | `VITE_API_URL` = API base above |
| Placeholder in HTML | `__CREDA_API_URL__` (sed-replaced at build) |

**If `/health` fails → STOP and report. Do not mock.**

---

## Files to read before coding

1. `docs/CREDA_UI_LLM_BUILD_SPEC.md` — API contract, tasks A–H, acceptance table  
2. `docs/CREDA_DESIGN_PHILOSOPHY_FOR_GEMINI.md` — design contract, tokens, motion grammar  
3. `docs/CREDA_CURSOR_UIUX_PROMPT.md` — kit decision table, inspiration index  
4. `frontend/index.html` — current implementation (functional but needs visual craft pass)  
5. `frontend/amplify.yml` — build pipeline  
6. `scripts/test_e2e_full.sh` — automated API smoke tests  

---

## API contract (real endpoints only)

Base URL baked at build: `__CREDA_API_URL__` → replaced with `VITE_API_URL`.

| Method | Path | Headers | Body |
|--------|------|---------|------|
| GET | `/health` | — | — |
| POST | `/cases` | `Content-Type: application/json` | `{ offerText, locale?, senderEmail?, employerHint?, screenshotKey?, screenshotSizeBytes? }` |
| GET | `/cases/{caseId}` | `X-Case-Token: <token>` | — |
| POST | `/cases/{caseId}/followup` | `Content-Type` + `X-Case-Token` | `{ answerText, question? }` |
| POST | `/upload-url` | `Content-Type: application/json` | `{ contentType }` → `{ uploadUrl, key }` then PUT file to `uploadUrl` |
| POST | `/reports/scam` | `Content-Type: application/json` | `{ reportText, employerHint?, contactConsent? }` |

### Create case response (verified live)
```json
{"caseId":"<uuid>","accessToken":"<token>","status":"QUEUED"}
```
Alias: `accessToken` may appear as `token` — handle both.

### Polling
- Interval: **1.5s**, max **~80 attempts** (~120s)  
- Stop when: `status === "COMPLETED"` AND `agentStatus === "READY"` AND `verdict` is real (not `pending`)  
- On `FAILED`: show `userMessage` or `nextAction`  

### Case JSON fields to render
`caseId`, `status`, `verdict`, `headline`, `evidence[]`, `matchedTactics[]`, `unresolved[]`, `checks[]`, `agentStatus`, `agentStreamText`, `agentProgress`, `agentReasoning`, `agentConfidence`, `agentGuardrailNote`, `agentSource`, `agentPresentation.blocks[]`, `conversationTurns[]`, `pipelineLog[]`, `nextActions[]`, `agentFollowups[]`

### Verdict values
- `high_risk` — conflicting evidence / scam signals → **don't pay, don't share IDs**  
- `unverified` — gaps remain → follow-up chips  
- `no_conflict_found` — aligned with employer policy → **never say "verified authentic offer"**

---

## Product UX: Ruling + Exhibits (not a chat dump)

### Intake screen
- H1: **"Check a job offer before you reply."**
- Large paste textarea (min 20 chars to submit)
- Collapsed **Add details**: sender email, employer hint, screenshot upload
- CTA: **Check this offer**
- Demo chips (fill fields, then hit **real API**):
  - **Amazon fee scam** — fee + Aadhaar demand
  - **Stripe clean** — real `gh_jid=8172510` careers link
  - **Vague ProtonMail** — uncertain recruiter
- Privacy: don't paste OTPs / bank / passwords

### Wait state (mock-browser chrome)
- Stage rail: **Intake → Evidence → Verdict → Judgment → Follow-up** (with icons + progress line)
- Elapsed timer `MM:SS`
- Mock browser URL bar showing real case id
- Stream panel bound to `agentStreamText` / `agentProgress` / `pipelineLog` with **shimmer**
- As `checks[]` and `evidence[]` arrive, show them live (slip-in animation)
- **Never** blank spinner for 60–120s

### Result state (judgment shell — liquid glass)
1. **Ruling stamp** — badge + headline + consequence + animated seal SVG  
2. **Creda explains its judgment** — collapsible; `agentReasoning` + confidence bar  
3. **What Creda checked** — research_status checklist  
4. **Verification exhibits** — bento grid, **flip cards** (front: They said / We checked; back: full excerpt)  
5. **Matched scam tactics** — if present  
6. **Still unknown** — uncertainty gaps  
7. **Immediate orders** — 2–3 actions; urgent pulse + sticky bar on mobile for `high_risk`  
8. **Need from you** — ≤3 follow-up chips + textarea  
9. **Full evidence dock** — accordion timeline of all evidence + checks + pipeline log  

### BLOCK_RENDERERS (implement all 9)
`verdict_banner`, `explanation`, `research_status`, `evidence_highlights`, `tactic_highlights`, `uncertainty`, `safe_actions`, `follow_up_questions`, `conversation`

If `agentPresentation.blocks` is empty, **synthesize from real case fields** — never invent fake scams.

### Plain-language check labels
Map `snake_case` → human labels, e.g.:
- `fee_policy` → Recruitment fee policy  
- `official_domain` → Official employer domain  
- `whatsapp_telegram_interview` → Interview via messaging app  

---

## Design system (required tokens)

```css
--ink: #0f2433;
--muted: #5f6d7a;
--bg: #f3f1ec;           /* warm paper */
--panel: #ffffff;
--line: #d7e0e8;
--blue: #155eef;         /* primary actions only */
--risk: #b42318;         /* high_risk */
--safe: #087443;         /* no_conflict_found */
--warn: #9a6700;         /* unverified */
--radius: 14px;
--font: 'Plus Jakarta Sans', system-ui, sans-serif;
```

**Visual bar:** Polished, artistic, visually stunning **and** job-done. Not Bootstrap. Not Tailwind marketing landing.

---

## Inspiration Index — RESEARCH ALL, then hand-port patterns

Open each URL. Decide **Use / Moodboard / Skip**. Implement chosen patterns in **vanilla CSS** inside `index.html`.

| URL | Decision | Creda surface |
|-----|----------|---------------|
| https://tweakcn.com/editor/theme | **USE** | Theme tokens |
| https://ui.rechesoares.com/docs/flip-card | **USE** | Exhibit flip front/back |
| https://ui.lukacho.com/components/mock-browser | **USE** | Wait / stream chrome |
| https://animata.design/docs/bento-grid | **USE** | Exhibit grid |
| https://www.ui-layouts.com/components/liquid-glass | **USE** | Judgment shell glass (readable text) |
| https://ai-sdk.dev/elements | **USE patterns** | Chips, reasoning disclosure, task status |
| https://coss.com/origin | **USE** | Input / Button / Badge / Accordion / Stepper feel |
| https://kokonutui.com/ | **USE** | Shimmer / entrance motion |
| https://www.cult-ui.com/ | Moodboard | Taste only |
| https://21st.dev/magic-chat | Moodboard | Composition |
| https://uiverse.io/ | Moodboard | One button/chip pattern max |
| https://lightswind.com/ | Moodboard | Motion taste |
| https://www.neobrutalism.dev/docs/chart | **SKIP** | No charts |
| https://www.reactbits.dev/text-animations/split-text | **SKIP** | No looping split-text |
| https://www.unicorn.studio/ | **SKIP** | No WebGL |
| https://reactnativereusables.com/docs | **SKIP** | Wrong platform |

### SVG / imagery
| Resource | Use |
|----------|-----|
| https://www.svgrepo.com/ | Primary stroke icons (shield, mail, alert, check, link, chevron) — **not emoji** |
| https://simpleicons.org/ | Tiny mono brand marks on demo chips (Gmail, WhatsApp) |
| https://undraw.co/illustrations | **≤1** empty-state illustration (case file / shield) — inline SVG preferred |
| https://www.vectorlogo.zone/ | Optional employer marks |

**Required graphics (inline SVG, not stock photos):**
- Brand shield mark in header  
- Stage rail icons (5 steps)  
- Idle-state trust illustration (case file + magnifier + shield)  
- Animated ruling stamp seal on verdict  
- Decorative background scene (subtle, low opacity)  
- Exhibit card corner fold / flip animation  

### Motion grammar (purposeful only; `prefers-reduced-motion` → instant)
- Page entrance fade-up  
- Stage progress line fill  
- Exhibit cards stagger slip-in  
- Stamp seal slam on verdict  
- Stream panel shimmer while judging  
- Urgent order single pulse + bottom sticky bar for high_risk  
- Button shine on hover  
- Floating ambient orbs (subtle)  

---

## Demo payloads (for chips — then call real API)

### Amazon fee scam
```
offerText: Your Amazon interview is confirmed for today. Please pay INR 1200 for training and send your Aadhaar over WhatsApp to proceed.
senderEmail: recruiter@amazon-careers.example
employerHint: Amazon
```
**Expected:** `high_risk`, fee policy conflict exhibits, don't-pay orders

### Stripe clean
```
offerText: Stripe is hiring Software Engineer. Apply at https://stripe.com/jobs/search?gh_jid=8172510. No fees required.
senderEmail: recruiting@stripe.com
employerHint: Stripe
```
**Expected:** vacancy match (T1), may be `unverified` if sender domain unproven — **honest limits**, not "authenticated"

### Vague ProtonMail
```
offerText: A recruiter met me after a conference and asked me to continue the software job conversation on WhatsApp. I am not sure how to verify the company.
senderEmail: talent-team@protonmail.com
employerHint: (empty)
```
**Expected:** `unverified` + follow-up chips

---

## Security & quality rules

### MUST
- `esc()` all dynamic HTML  
- Token in memory + `sessionStorage` only — never URL, never `console.log`  
- Real API only — zero mock branches  
- Handle 4xx/5xx/timeouts with friendly copy  
- Mobile-first; sticky urgent bar on `high_risk`  
- `aria-live` on result region  

### MUST NOT
- Marketing hero / feature grids  
- Fake "API unavailable" without real failed `/health`  
- Charts, WebGL, looping split-text  
- `alert()` for normal errors  
- Claim verified authentic offer  
- Open PR unasked  

---

## Build & deploy

### Local build check
```bash
cd frontend
export VITE_API_URL="https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com"
mkdir -p dist
sed "s|__CREDA_API_URL__|$VITE_API_URL|g" index.html > dist/index.html
grep -q "__CREDA_API_URL__" dist/index.html && echo "FAIL: placeholder leaked" && exit 1
echo "OK"
```

### Deploy to Amplify (manual)
```bash
API="https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com"
cd frontend
sed "s|__CREDA_API_URL__|$API|g" index.html > dist/index.html
DEPLOY=$(aws amplify create-deployment --app-id d32sg54oqu2gcb --branch-name main --region ap-south-1 --profile creda-dev --output json)
JOB=$(echo "$DEPLOY" | jq -r .jobId)
URL=$(echo "$DEPLOY" | jq -r .zipUploadUrl)
(cd dist && zip -r -q ../deploy.zip .)
curl -s -X PUT -T deploy.zip -H "Content-Type: application/zip" "$URL"
aws amplify start-deployment --app-id d32sg54oqu2gcb --branch-name main --job-id "$JOB" --region ap-south-1 --profile creda-dev
```

### API E2E smoke (backend correctness)
```bash
CREDA_API_URL="$API" bash scripts/test_e2e_full.sh
# Expect: ALL E2E CHECKS PASSED
```

---

## Acceptance tests (manual — must pass before claiming done)

| # | Scenario | Pass criteria |
|---|----------|---------------|
| H1 | Health | Badge shows live when `dataReady` true |
| H2 | Amazon fee scam | Real `high_risk`; exhibits cite evidence; don't-pay orders |
| H3 | Stripe demo | Honest verdict; vacancy exhibit if matched; not "authenticated" |
| H4 | Vague message | `unverified` + follow-up chips work |
| H5 | Short input | Validation message; no API spam |
| H6 | Wait UX | Evidence visible before ruling; timer runs; stream updates |
| H7 | Mobile | Readable; urgent sticky on high_risk |
| H8 | No mocks | Network tab shows only `ap-south-1.amazonaws.com` |

**Also verify in browser:** flip exhibits, judgment accordion, screenshot upload flow, report scam accordion.

---

## Known backend behavior (render honestly)

- `agentSource: "creda"` = SageMaker Qwen judge succeeded  
- `agentSource: "fallback"` = rule-based backup (show guardrail note; don't fake Qwen reasoning)  
- Stripe with real `gh_jid` may still be `unverified` if sender email isn't verified — UI must explain gaps  
- Judging takes **30–90s** — wait UI is critical  
- Screenshot: presign → PUT → include `screenshotKey` in case create  

---

## Build sequence (execute in order)

1. **Preflight** — `/health`, one real `POST /cases`, poll until READY; record payload shape  
2. **Scaffold** — tokens, scene background SVG, header, stage rail with icons  
3. **Intake** — glass case-file card, rich idle illustration, demo chips with icons  
4. **Live loop** — create / poll / follow-up / upload / report  
5. **Wait** — mock-browser, shimmer stream, live evidence badges  
6. **Result** — all BLOCK_RENDERERS, flip bento, stamp animation, orders, chips  
7. **Craft pass** — motion, reduced-motion, mobile, a11y  
8. **Deploy** — Amplify build + browser verify H1–H8  
9. **Report** — what passed, screenshots, any blockers  

---

## Definition of done

A judge opens `https://main.d32sg54oqu2gcb.amplifyapp.com`, pastes the fee-scam demo, watches **real** evidence arrive in a **visually crafted** UI (SVG icons, glass, flip exhibits, animations), gets a **ruling stamp + exhibit slips** explaining *why*, can follow up — zero mocks, zero marketing-landing look.

**Start now.** Read the docs listed above, verify `/health`, then rebuild `frontend/index.html` with full visual craft. Deploy to Amplify when H1–H8 pass.
