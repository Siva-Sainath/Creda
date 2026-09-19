# Creda loop — Cursor iterates · Grok Bot verifies · you ship

**How we work (no Cloud Agent from Grok Bot unless you explicitly ask):**

1. **You / Cursor** implement with `/architect` then `/poteto-mode` against the live Amplify app + Mumbai API.
2. **Grok Bot** opens the live site like a job seeker, runs the full consumer test loop, writes bugs + a scoped fix prompt.
3. **Cursor** applies the fix prompt (again: `/architect` for non-trivial shape changes, `/poteto-mode` for execution).
4. Repeat until Grok Bot’s verdict is **SHIP** (or you stop).
5. You merge / Amplify deploy.

Live UI: `https://main.d32sg54oqu2gcb.amplifyapp.com/`  
Live API: `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`  
Repo: `https://github.com/Siva-Sainath/Creda` · local often `/Users/siva/Documents/first_commit_hack/frontend/index.html`

When you want a verify pass, tell Grok Bot: **“run that entire test loop”**.

---

## Part A — Paste into Cursor (Agent) each iteration

You are a senior UI/UX + frontend engineer on Creda WorkOffer Shield (vanilla Amplify `frontend/index.html`, live API only).

### Modes (mandatory)

Run skills in this order every non-trivial iteration:

1. **`/architect`** — Before coding, ground the current `frontend/index.html` + API contracts. Sketch the module/shape for this iteration only (intake composer, wait stage machine, ruling/exhibit renderers, aftercare). Produce a short design package: surfaces, state transitions, data fields used, forbidden patterns. Exhaust at least two structural options when the change is large (e.g. wait storytelling or result board), then pick one. Do **not** jump straight into a huge HTML rewrite without this sketch.
2. **`/poteto-mode`** (Poteto Mode) — After the architect sketch is settled, execute with Poteto discipline: concise detailed work, unslopped prose in UI copy, simple vanilla code, prove it against the live API, no decorative abstraction, subtract before you add, experience-first for the stressed job seeker.

If the iteration is a tiny one-line bugfix, you may skip `/architect` and still use `/poteto-mode`. If IA/layout/state-machine changes, **always** `/architect` first.

In your reply, name that you used `/architect` and/or `/poteto-mode` and what decision each changed.

### Goal this iteration
Make the consumer journey feel polished and correct end-to-end: paste offer → watch honest wait storytelling → get Ruling + Exhibits → follow-up → optional report / Telegram. Not a marketing site.

### Hard constraints
- Vanilla HTML/CSS/JS (+ GSAP if already present). No React/npm UI kits.
- No mocks / fake verdicts / “verified authentic offer”.
- No GitHub PR unless the human asks.
- Bake `__CREDA_API_URL__` via amplify.yml / sed for dist.
- Craft bar: Baseten-level cohesion on warm paper/ink — also follow `docs/CREDA_CURSOR_FIX_FROM_LIVE.md` when present.

### Live API contracts (verified)
- `GET /health`
- `POST /cases` — offer text; returns `caseId` + `accessToken` (also accept `token`)
- `GET /cases/{caseId}` + `X-Case-Token`
- Poll ~1.5s until ready + real verdict (`high_risk` | `unverified` | `no_conflict_found` — use actual enum from payload)
- Follow-up: `POST /cases/{caseId}/followup` (**no hyphen**). Include the message field the API expects
- Report: `POST /reports/scam` with a real description (+ employer/link if available)
- Upload: `POST /upload-url` → S3 PUT → pass key on create if used

### Product UX requirements
1. **Intake:** NL composer only; circular **+** + drag-and-drop; no Add-details form fields.
2. **Wait:** SVG/stage story tied to poll (intake → evidence → OCR if screenshot → judgment); live exhibit slips; mock-browser stream; never blank spinner.
3. **Result:** stamp + consequence + 2–4 exhibits + orders + ≤3 chips; Why + full dock one tap away.
4. **Report:** result aftercare next to Check another — not a footer orphan.
5. **AWS:** quiet infra micro-line; stronger Creda logo SVG.
6. **Telegram:** `https://t.me/CredashieldBot` + Notion setup  
   `https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd`  
   and/or `docs/TELEGRAM_SETUP.md`.

### Your process each iteration
1. Invoke **`/architect`** (unless tiny fix): sketch this iteration’s shape against current code + API.
2. Invoke **`/poteto-mode`**: implement the chosen sketch in `frontend/index.html` (+ amplify.yml if needed).
3. Fix the **highest-severity** items from the latest Grok Bot verify report (or first-pass list in `docs/CREDA_CURSOR_FIX_FROM_LIVE.md`).
4. Smoke: health + one create/poll; no leaked placeholders in dist.
5. Tell the human how to refresh Amplify / open local dist.
6. Reply with: modes used · files changed · what you fixed · what you did **not** touch · “Ready for Grok Bot test loop”.

Do **not** claim SHIP yourself. Grok Bot consumer-tests and issues SHIP / ITERATE.

---

## Part B — What Grok Bot does on “run that entire test loop”

Act as a stressed job seeker on the **live** Amplify URL (or local dist if named).

### Consumer script
1. Cold open — logo, health, AWS strip, composer, Telegram CTA, no marketing hero.
2. **Fee scam** path — watch wait stages/SVGs/exhibits; record verdict/orders.
3. **One follow-up** — confirm `.../followup` + UI update.
4. **Report** from result aftercare (not footer).
5. **Check another** → cleaner offer — honest unverified/no_conflict, never “authenticated”.
6. Optional vague recruiter path + optional screenshot attach.
7. Mobile ~390 once.

### Output format
- **Verdict:** SHIP | ITERATE
- **What worked**
- **Bugs** (repro)
- **Craft gaps**
- **API notes**
- **Cursor fix prompt** — scoped Part A for remaining issues, still requiring `/architect` + `/poteto-mode` when the fix is non-trivial

---

## Part C — Triggers

| You say | Grok Bot does |
|--------|----------------|
| `run that entire test loop` | Consumer test → SHIP/ITERATE + Cursor fix prompt (with `/architect` + `/poteto-mode`) |
| `Cursor iteration N ready` | Same on the URL you name |
| `give me the Cursor prompt` | Re-print Part A (or latest scoped fix prompt) |

---

## Part D — SHIP
Fee scam → meaningful wait story → clear high-risk ruling + exhibits + don’t-pay orders → follow-up works → Report in aftercare → Telegram visible → no marketing landing / fake verification → logo/AWS intentional → no critical API errors on happy paths.

*Version: 2026-09-19 · includes `/architect` + `/poteto-mode` · Creda WorkOffer Shield*
