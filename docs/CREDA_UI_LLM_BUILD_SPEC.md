# Creda UI — LLM Build Spec (End-to-End, Real Backend Only)

**Audience:** An implementing LLM / coding agent  
**Product:** Creda WorkOffer Shield  
**Mode:** Build and ship — **no mocks, no fake JSON fixtures in production paths**  
**Do not open GitHub PRs unless the human explicitly asks.**

---

## 0. Mission

Replace / rebuild `frontend/index.html` into a production single-page UI that:

1. Talks **only** to the live AWS API and renders **real** case / evidence / Qwen presentation data.
2. Presents results as **Ruling + Exhibits** so a stressed job seeker understands *why* an offer is or is not a scam.
3. Feels polished (purposeful motion, glass, cards) without vibe-kit dumping.
4. Deploys cleanly on **AWS Amplify Hosting** (static HTML).

**Success = a judge can open the live Amplify URL, paste a demo offer, watch real evidence arrive, see a real Qwen ruling, follow-up, and never hit a mock path or a raw error.**

---

## 1. Live backend (source of truth — verify before coding)

| Item | Value |
|------|--------|
| API base | `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com` |
| Region | `ap-south-1` |
| Amplify app | `creda-mvp` (`d32sg54oqu2gcb`) |
| Amplify URL | `https://main.d32sg54oqu2gcb.amplifyapp.com` |
| Health | `GET /health` → expect `{"status":"ok","dataReady":true,...}` |
| Frontend source | `/Users/siva/Documents/first_commit_hack/frontend/index.html` (or repo `Siva-Sainath/Creda` `frontend/`) |
| Amplify build | `frontend/amplify.yml` sed-bakes API URL into `__CREDA_API_URL__` |

### Required preflight (must pass; fail the task if not)

```bash
curl -sS "$API/health"
# Expect HTTP 200 and dataReady true
```

If health fails: **stop and report**. Do not invent a mock health response.

---

## 2. Absolute rules

### MUST
- Call real endpoints for all product flows (create case, poll, follow-up, report, health).
- Use `X-Case-Token` from the create-case response for subsequent GETs/follow-ups.
- Store token in memory + `sessionStorage` only — **never** in URL/query/localStorage logs.
- Escape all dynamic text (`esc()` or equivalent) before `innerHTML`.
- Preserve / implement all 9 `BLOCK_RENDERERS` types from the backend schema.
- Keep vanilla HTML + CSS + JS (no React/npm bundle) unless human changes stack.
- Align `amplify.yml` env var name with the sed placeholder (today: `VITE_API_URL` → `__CREDA_API_URL__`).
- Handle CORS, 4xx/5xx, timeouts, empty blocks with **user-readable** messages + nextAction style hints.
- Optimize for Amplify: single `index.html` (or tiny assets), no unused fonts/CDN bloat, `prefers-reduced-motion`, mobile-safe.

### MUST NOT
- Mock cases, verdicts, evidence, or agentPresentation in the shipped UI.
- Hardcode fake `caseId` / tokens.
- Use charts (neobrutalism), Unicorn WebGL, looping split-text, RN kits.
- Open GitHub PRs unless asked.
- Claim “verified authentic offer” on `no_conflict_found`.
- Show raw stack traces, browser `alert()` for normal errors, or log offer text / tokens.

---

## 3. Product narrative (who / when / output)

- **Who:** Job seekers in India (and global) who received a recruitment email/SMS/WhatsApp/chat.
- **When:** Before they pay a fee or share documents.
- **Output:** A **ruling** with **exhibits** (facts), **orders** (actions), and **need from you** (follow-ups), backed by Lambda evidence + Qwen3-4B presentation on ECS.

**WeMakeDevs / judges:** One flow end-to-end; frontend sells the backend; slow work must show visible state; bad input → readable message; Best UI = polish *and* clarity.

---

## 4. UX: Ruling + Exhibits (do not ship a chat dump)

### Always visible after judgment (the ~80%)
1. **Ruling stamp** — `high_risk` | `unverified` | `no_conflict_found` in plain words + one consequence line  
2. **2–4 Exhibit slips** — each: They said / We checked / Result / Tier (T1|T2) / optional source  
3. **Orders** — 2–3 `safe_actions` (urgent sticky on mobile for high_risk)  
4. **Need from you** — ≤3 follow-up chips  

### One tap away (the ~20%)
- **Why this ruling** — `agentReasoning` + explanation (label: “Creda explains its judgment”, not chain-of-thought)  
- **Full evidence dock** — all Lambda `evidence[]` + `checks[]` timeline  

### During wait (real data only)
- Poll real case; as soon as `evidence` exists (`COMPLETED` + `verdict=pending` or streaming), **render real evidence cards**  
- Elapsed timer; distinct state for evidence-running vs Qwen-judging  
- `agentStreamText` in a mock-browser-style panel when present  
- Never a blank spinner for 60–120s  

### Intake (single product screen)
- H1: “Check a job offer before you reply.”  
- Large paste box; **Add details** collapsed (sender, employer, links)  
- CTA: **Check this offer**  
- Demo chips that fill the textarea with realistic full messages (then hit real API)  
- Secondary after result: Check another / Report this scam (report can be footer accordion)  
- No login, dashboard, settings, onboarding  

---

## 5. Real API contract (implement exactly)

Base = baked `__CREDA_API_URL__` (fallback only for local: the live ap-south-1 URL above).

| Method | Path | Headers | Body | Success |
|--------|------|---------|------|---------|
| GET | `/health` | — | — | status, dataReady |
| POST | `/cases` | `Content-Type: application/json` | `{ offerText, locale?, senderEmail?, employerHint? }` | `{ caseId, accessToken }` (field names: use whatever live API returns — verify with one real call; common aliases `token` vs `accessToken`) |
| GET | `/cases/{caseId}` | `X-Case-Token: <token>` | — | case JSON (see fields) |
| POST | `/cases/{caseId}/followup` | `Content-Type` + `X-Case-Token` | `{ answerText, question? }` | then poll again |
| POST | `/reports/scam` | `Content-Type` | `{ reportText, employerHint?, contactConsent? }` | receipt message |

### Polling
- Interval **1.5s**, max **~120s** (≈80 attempts)  
- States:
  - `QUEUED` / `RUNNING` → evidence stage UI  
  - `COMPLETED` + (`verdict` missing/`pending` OR `agentStatus` in PENDING|RUNNING|STREAMING) → show evidence + judging UI  
  - `COMPLETED` + `agentStatus=READY` + real verdict → Ruling + Exhibits  
  - `FAILED` → userMessage / nextAction  

### Case JSON fields to consume (real)
`caseId`, `status`, `verdict`, `headline`, `evidence[]`, `matchedTactics[]`, `unresolved[]`, `checks[]`, `agentStatus`, `agentStreamText`, `agentReasoning`, `agentConfidence`, `agentGuardrailNote`, `agentPresentation: { version, blocks[] }`, `conversationTurns[]`, `stage` if present.

### Block types (render all; skip unknown)
`verdict_banner`, `explanation`, `research_status`, `evidence_highlights`, `tactic_highlights`, `uncertainty`, `safe_actions`, `follow_up_questions`, `conversation`

**If `blocks` empty:** build fallback UI from `verdict` + `headline` + `evidence` + `matchedTactics` + `unresolved` (still real fields — not invented scams).

### Plain-language check labels (examples)
- `free_mailbox` → Sender used a free email, not a company domain  
- `fee_policy` → Fee demand vs employer “we never charge” policy  
- `official_domain` → Sender domain vs official employer domain  
Map others similarly; never leave raw snake_case as the only label.

---

## 6. Design system + kit map (hand-rebuild in vanilla CSS/JS)

**Tokens:** `--ink #0f2433`, `--bg` warm paper, `--panel #fff`, `--risk #b42318`, `--safe #087443`, `--warn #9a6700`, `--blue #155eef`, radius 12–16px.

| Piece | Inspire from | Implement as |
|-------|--------------|--------------|
| Theme | tweakcn | CSS variables |
| Input/Button/Badge/Alert/Accordion/Stepper | coss.com/origin | Hand CSS |
| Exhibit grid | animata bento | CSS grid |
| Exhibit detail | flip-card | CSS flip; ruling never flips |
| Judgment shell | selective liquid-glass | light backdrop-filter |
| Chips / why / pipeline | AI Elements Suggestions, Reasoning, Task | Hand JS+CSS |
| Stream chrome | lukacho mock-browser | HTML frame |
| Shimmer | kokonut | CSS keyframes |
| Icons | SVG Repo + Simple Icons | Inline SVG |
| Empty state | Undraw (≤1) | Optional |

**Skip:** neobrutalism charts, unicorn.studio WebGL, reactbits split-text loops, react-native reusables, npm React kits in Amplify build.

**Motion (purposeful only):** exhibit slip-in when evidence arrives; stamp land on READY; stream shimmer while STREAMING; urgent order single pulse. Respect `prefers-reduced-motion`.

---

## 7. Task list (execute in order; check off)

### Phase A — Discover & lock contract
- [ ] **A1.** `GET /health` against live API; record response.  
- [ ] **A2.** Create one real case with a **full** demo message (Amazon fee style); record exact response keys (`caseId`, `accessToken` vs `token`).  
- [ ] **A3.** Poll until READY; save one real COMPLETED payload shape (sanitize secrets in notes).  
- [ ] **A4.** Confirm CORS works from `file://` or local static server and from Amplify origin; if CORS blocks Amplify origin, document required `AllowOrigins` change for backend owners (do not fake success).  
- [ ] **A5.** Read `frontend/amplify.yml` and current `index.html` placeholder; lock env var name (`VITE_API_URL` vs `CREDA_API_URL`) so build cannot ship `__CREDA_API_URL__` unbroken.

### Phase B — Shell UI (still no mocks)
- [ ] **B1.** Rebuild page structure: header, composer, stepper, result region, footer trust/report.  
- [ ] **B2.** Implement tokens + responsive layout (mobile single column).  
- [ ] **B3.** Wire demo chips → fill fields only (submit still hits real API).  
- [ ] **B4.** Inline SVG icon set (shield, mail, alert, check, link, chevron).

### Phase C — Live intake + poll
- [ ] **C1.** `POST /cases` with real body; validate `caseId` + token; persist token.  
- [ ] **C2.** Poll loop 1.5s / 120s with abort on leave/reset.  
- [ ] **C3.** Waiting UI: timer + stage labels + **real** `evidence`/`checks` as soon as present.  
- [ ] **C4.** Stream panel bound to real `agentStreamText`.  
- [ ] **C5.** Error paths: short offer, 400, 404 bad token, 503, network, timeout — friendly copy, no alerts.

### Phase D — Ruling + Exhibits from real agentPresentation
- [ ] **D1.** `BLOCK_RENDERERS` for all 9 types; map to stamp / exhibits / orders / chips / conversation.  
- [ ] **D2.** Narrative order: stamp → so what → why (collapsible) → exhibits → tactics → uncertainty → orders → follow-ups → evidence dock.  
- [ ] **D3.** Verdict-specific copy rules (high_risk / unverified / no_conflict_found honesty).  
- [ ] **D4.** `agentConfidence` meter only if present; `agentGuardrailNote` footnote.  
- [ ] **D5.** Sticky urgent orders on mobile.  
- [ ] **D6.** Fallback synthesizer from real case fields if blocks missing.

### Phase E — Follow-up + report (real)
- [ ] **E1.** Chip → prefill follow-up textarea; `POST .../followup`; re-poll; show `conversation` if returned.  
- [ ] **E2.** Report accordion → `POST /reports/scam`; show real receipt/error.  
- [ ] **E3.** Check another clears case state safely.

### Phase F — Polish + a11y + performance
- [ ] **F1.** Purposeful motion only (see §6); reduced-motion path.  
- [ ] **F2.** Keyboard: submit, chips, flip, accordion.  
- [ ] **F3.** `aria-live` on result region; don’t rely on color alone for verdict.  
- [ ] **F4.** Asset budget: prefer system/Inter CDN once max; no heavy libraries.  
- [ ] **F5.** Ensure no offer text / tokens in `console.log`.

### Phase G — Deploy optimization
- [ ] **G1.** `amplify.yml`: fail build if env URL missing; sed produces `dist/index.html` with **real** API host (zero `__CREDA` leftovers).  
- [ ] **G2.** Build locally: `mkdir -p dist && sed "s|__CREDA_API_URL__|$VITE_API_URL|g" index.html > dist/index.html` and grep dist for placeholder.  
- [ ] **G3.** Document Amplify env: `VITE_API_URL=https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com` (or rename consistently).  
- [ ] **G4.** Cache headers / single artifact; no source maps required.  
- [ ] **G5.** Smoke on Amplify after deploy (or instruct human): health line, Fee scam demo E2E, bad token path, mobile sticky.

### Phase H — Acceptance tests (manual, against live API)

| # | Scenario | Pass criteria |
|---|----------|----------------|
| H1 | Health | UI shows API ready when `dataReady` |
| H2 | Fee scam demo | Real high_risk or equivalent; exhibits cite real evidence; orders include don’t pay |
| H3 | Clean careers-style demo | no_conflict_found or unverified with honest limits; not “authenticated” |
| H4 | Vague message | unverified + follow-up chips; chips trigger real reverify |
| H5 | Short input | Friendly validation; no API spam |
| H6 | Wait UX | Evidence visible before final ruling when API provides it; timer increments |
| H7 | Mobile | Readable; urgent sticky if high_risk |
| H8 | No mocks | Network tab shows only real API hosts; no fixture JSON |

---

## 8. Files to touch

| File | Action |
|------|--------|
| `frontend/index.html` | Primary deliverable — full UI + API client + renderers |
| `frontend/amplify.yml` | Ensure env/sed correct; fail closed if URL missing |
| `frontend/dist/` | Build output only (generated) |
| Optional `docs/` note | Deploy steps for human |

Do **not** change Qwen `judge.py` / `presentation.py` unless a real schema mismatch blocks rendering — prefer UI aliases. If backend field names differ from this spec, **follow the live payload**.

---

## 9. Copy constraints

- “Creda explains its judgment” — not chain-of-thought.  
- `no_conflict_found` ≠ verified sender/offer.  
- Privacy hint: don’t paste passwords, OTPs, bank, ID numbers.  

---

## 10. Definition of Done

- [ ] Live Amplify (or local dist pointed at live API) completes H1–H8.  
- [ ] Zero mock branches in production code paths.  
- [ ] Zero uncaught UI errors on happy path + listed error paths.  
- [ ] `amplify.yml` build cannot emit unbroken `__CREDA_API_URL__`.  
- [ ] Ruling + Exhibits narrative implemented with purposeful motion.  
- [ ] Written smoke notes: what was called, verdicts seen, any CORS/backend blockers.

---

## 11. Prompt blurb (paste to the implementing LLM)

> Implement Creda’s frontend per `docs/CREDA_UI_LLM_BUILD_SPEC.md`. Connect only to the live API `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`. No mocks. Build Ruling + Exhibits UI, wire all endpoints, optimize `amplify.yml` deploy, run the acceptance table against real data. Do not open a PR unless I ask. Report blockers (CORS, schema drift) instead of faking success.

---

*Spec version: 2026-09-18 · Creda WorkOffer Shield · Real backend only*
