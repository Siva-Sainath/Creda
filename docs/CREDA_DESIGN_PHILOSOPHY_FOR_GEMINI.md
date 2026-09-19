# Creda Design Philosophy + Gemini Build Brief

**Product:** Creda / WorkOffer Shield  
**Surface type:** Single-screen **tool** (not marketing, not dashboard)  
**Stack:** Vanilla HTML/CSS/JS → AWS Amplify static hosting  
**Backend:** Live API only — `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`  
**Also read:** `docs/CREDA_UI_LLM_BUILD_SPEC.md` (tasks A–H, endpoints, acceptance)

---

## How to make an agent actually build useful UI

Research-backed rules for Gemini (and any coding agent):

1. **Give a design contract, not adjectives.** “Modern / premium / ElevenLabs-like” → generic SaaS. Instead: surface type, user intent, priority order, forbidden patterns, tokens, allowed components.
2. **Name the user task in under one minute.** Who, fear, decision, next action.
3. **Forbid failure modes explicitly.** Marketing heroes, nested card soup, fake “API unavailable” chrome, charts, invented components.
4. **Separate DESIGN (look/feel) from BUILD (API/deploy).** This file = DESIGN + prompt. Spec file = engineering checklist.
5. **Require verification.** Health check, network-tab real host, acceptance scenarios — not “looks nice.”
6. **Kits are patterns to hand-port**, not `npm install` dumps (Amplify = single HTML).

---

# Part A — Design philosophy (Creda)

## A1. Who and what this screen is for

| Field | Value |
|-------|--------|
| User | Job seeker (India-first) who just got a recruitment email/SMS/WhatsApp/chat |
| Moment | Seconds before they pay a fee or share documents |
| Fear | Losing money / ID; also fear of missing a real job |
| Task (<60s) | Paste message → understand **is this risky or not, and why** → know what to do |
| Success | They leave with a clear ruling, 2–4 checkable facts, and concrete next steps — without reading a wall of text |
| Risk if UI fails | They ignore the tool (ugly/confusing) OR they trust a fake “verified” badge |

**Surface type:** Tool / case workspace.  
**Not:** Landing page, docs site, analytics dashboard, AI chat playground clone.

**WeMakeDevs / judges:** Frontend sells the backend. One flow end-to-end. Slow work must show visible state. Bad input → readable message. Best UI = clarity + craft, not decoration.

## A2. Information philosophy — Ruling + Exhibits

Borrowed from frontier AI (Perplexity answer-first + citations; Claude readable calm) and decision UX (verdict → reasons → consequence → next action) — **adapted**, not copied.

### Always on (80% of users)
1. **Ruling stamp** — High risk / Not enough proof / No conflict found + one consequence line  
2. **2–4 Exhibit slips** — each one fact a human can grasp in ~3 seconds:
   - They said  
   - We checked  
   - Result (conflict / clear / unknown)  
   - Tier (T1 official / T2 pattern)  
   - Optional source link  
3. **Orders** — 2–3 next actions (urgent sticky on mobile if high risk)  
4. **Need from you** — ≤3 follow-up chips  

### One tap away (20%)
- **Why this ruling** — Qwen 2–3 sentences (“Creda explains its judgment”)  
- **Full evidence dock** — all Lambda evidence/checks  

### While waiting (must feel alive and honest)
- Stage rail: Intake → Evidence → Verdict → Judgment → Follow-up  
- Real evidence cards as API returns them  
- Elapsed timer  
- Stream panel for `agentStreamText` (mock-browser chrome)  
- Never blank spinner for 60–120s  

### Verdict honesty
| Verdict | Lead with | Never say |
|---------|-----------|-----------|
| high_risk | Conflicting exhibits + don’t pay / don’t share IDs | Vague “suspicious” |
| unverified | Gaps + follow-ups | Fake certainty |
| no_conflict_found | What aligned + limits | “Verified authentic offer/sender” |

## A3. Visual language

**Metaphor:** Case file / recruitment ruling board — calm, precise, trustworthy under stress.

**Tokens (required):**
```css
--ink: #0f2433;
--muted: #5f6d7a;
--bg: #f3f1ec;          /* warm paper */
--panel: #ffffff;
--line: #d7e0e8;
--blue: #155eef;        /* primary actions only */
--risk: #b42318;        /* high_risk */
--safe: #087443;        /* no_conflict_found */
--warn: #9a6700;        /* unverified / judging */
--radius: 14px;
--font: Inter, ui-sans-serif, system-ui, sans-serif;
```

**Typography:** Few sizes. Ruling is the loudest text after the CTA. Body readable grey. No slogan all-caps marketing overlines as the product identity.

**Density:** Standard tool density — generous on desktop (max content width ~720–880px), single column on mobile.

**Elevation:** Soft borders + very light shadow. Soft glass **only** on judgment shell / exhibit cards (readable text). No heavy WebGL.

## A4. Motion grammar (purposeful only)

Animation must **explain state**. If you can’t say what it tells the user, delete it.

| Trigger | Motion | Duration feel |
|---------|--------|----------------|
| Evidence arrives | Exhibit slip slides/fades in | ~200–300ms |
| Qwen STREAMING | Stream panel shimmer | continuous, subtle |
| agentStatus READY | Ruling stamp lands | ~300–400ms |
| high_risk urgent order | Pulse once, then still | one pulse |
| Chip / button press | Quick press feedback | ~100–150ms |

`prefers-reduced-motion: reduce` → instant state, no parallax/fog.

## A5. Forbidden patterns (reject build if present)

- Marketing hero (“A calmer second opinion…”, brand manifesto, feature grid landing)
- Default state “Live API unavailable” without a real failed `/health` call
- Nested card-in-card decoration with no fact
- Charts / neobrutal analytics
- Looping split-text / Unicorn Studio WebGL backgrounds
- ChatGPT clone sidebar + infinite thread as the main product
- Fake demo data / mocked verdicts in production paths
- Invented block types outside the backend schema
- `alert()` for normal errors; logging offer text or tokens

## A6. Kit consolidation — what to use (hand-port to vanilla)

| Priority | Source | Use for Creda |
|----------|--------|----------------|
| P0 | **tweakcn** | Theme tokens only |
| P0 | **coss.com/origin** | Input, Button, Badge, Alert, Accordion, Stepper feel |
| P0 | **animata bento** | Exhibit grid layout |
| P0 | **SVG Repo** | One-stroke shield/mail/alert/check/link/chevron |
| P1 | **flip-card** | Exhibit front/back only (never ruling) |
| P1 | **liquid-glass** (ui-layouts) | Soft judgment shell only |
| P1 | **AI Elements** (Prompt/Suggestions/Reasoning/Sources/Task patterns) | Paste chips, why disclosure, stage status — not full React install |
| P1 | **mock-browser** (lukacho) | Stream wait chrome |
| P1 | **kokonutui** | Shimmer / entrance motion taste |
| P1 | **Simple Icons** | Tiny mono Gmail/WhatsApp on demos |
| P2 | **Undraw** | ≤1 empty-state illustration |
| P2 | **21st.dev / cult-ui / Lightswind / uiverse / CodePen** | Moodboard one idea max |
| Skip | neobrutalism charts, unicorn.studio, reactbits split-text, nextbunny-as-runtime, react-native reusables, Framer kit dumps | |

**Implementation rule:** Amplify = **one `index.html` (+ amplify.yml)**. Steal structure/CSS ideas; do not ship React/npm UI kits unless human changes stack.

## A7. Qwen3-4B control surface

Frontend owns layout. Qwen only fills short JSON slots (`agentPresentation.blocks` + reasoning).  
Max ~3–4 exhibits, short strings, fixed block types only.  
Never ask the model for HTML, markdown tables, or layouts.

---

# Part B — Gemini prompt (copy everything below the line)

--------------------------------------------------------------------------------
GEMINI — BUILD CREDA UI NOW

You are a senior product designer + frontend engineer. Build the Creda WorkOffer Shield **tool UI**, not a marketing site.

### Read before coding
1. This file: `docs/CREDA_DESIGN_PHILOSOPHY_FOR_GEMINI.md` (design contract)
2. `docs/CREDA_UI_LLM_BUILD_SPEC.md` (API, tasks A–H, acceptance H1–H8)
3. Existing `frontend/index.html` and `frontend/amplify.yml`

### Surface
- Type: **tool** / single case workspace
- User intent: paste recruitment message → get ruling + exhibits + next steps
- Density: standard; mobile-first single column
- Allowed building blocks: ruling stamp, exhibit slips (bento), orders, follow-up chips, stage stepper, stream mock-browser, accordion evidence dock, composer with collapsed details
- Tokens: exactly as in §A3
- Forbidden: everything in §A5 (especially marketing heroes and fake API-unavailable chrome)

### Engineering (non-negotiable)
- Live API only: `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`
- No mocks. Wire POST /cases, GET /cases/{id} + X-Case-Token, POST followup, POST /reports/scam, GET /health
- Poll 1.5s / ~120s; show real evidence during wait
- Vanilla HTML/CSS/JS for Amplify; sed `__CREDA_API_URL__` via amplify.yml (match VITE_API_URL unless you fix both consistently)
- Escape all dynamic text; never log secrets
- Do not open a GitHub PR unless I say so

### Design craft to implement
Hand-port patterns from: tweakcn tokens, coss primitives, animata bento exhibits, flip-card on exhibits, soft liquid-glass on judgment shell, AI Elements-style chips/reasoning/stages, mock-browser stream, kokonut-like shimmer, SVG Repo + Simple Icons.
Purposeful motion only (§A4).

### Process
1. GET /health — report real result
2. Rewrite `frontend/index.html` to the product screen (§A2)
3. Complete tasks A–H from the build spec
4. Run acceptance H1–H8 against live API
5. Report: what you built, network proof (real host), any CORS/schema blockers — never fake success

### Success condition
A judge opens Amplify URL, runs the fee-scam demo, sees live pipeline, gets Ruling + Exhibits that explain WHY, can follow-up — with craft (glass/bento/motion) serving comprehension, not decoration. Zero marketing-landing look.

Start now: health check, then rewrite the product UI.
--------------------------------------------------------------------------------

---

# Part C — Quick anti-slop checklist for review

Reject Gemini’s output if:
- [ ] Looks like a generic Tailwind landing page
- [ ] No exhibit slips / ruling stamp
- [ ] API not called on Check this offer
- [ ] Wait state is only a spinner
- [ ] “Unavailable” without a real failed health request
- [ ] Charts, WebGL, looping headline animations
- [ ] Claims verified authentic offer

Accept if:
- [ ] Ruling + Exhibits narrative clear in <5 seconds
- [ ] Real network calls to ap-south-1 API
- [ ] Evidence during wait from real payload
- [ ] Kit patterns visible but purposeful
- [ ] Amplify dist has real API URL baked in

*Version: 2026-09-18 · For Gemini · Creda WorkOffer Shield*
