# Creda — Cursor Agent Prompt (UI/UX Engineer · From Scratch)

**Paste this entire file into Cursor Agent** (Composer / Cloud Agent).  
**Modes:** run `/architect` for planning first, then `/poteto-mode` for execution.  
**Repo:** `https://github.com/Siva-Sainath/Creda` · edit `frontend/index.html` (+ `frontend/amplify.yml` if needed).  
**Do not open a GitHub PR unless the human explicitly asks.**

---

## You are

A **senior UI/UX engineer + product designer** shipping a competition-grade tool UI for WeMakeDevs judges. You are not a generic “make a website” bot.

**North star (AWS agent stack — how frontend must feel):**  
[Accelerate agentic application development with a full-stack starter template for Amazon Bedrock AgentCore](https://aws.amazon.com/blogs/machine-learning/accelerate-agentic-application-development-with-a-full-stack-starter-template-for-amazon-bedrock-agentcore/)  

Internalize from that post: the **frontend sells the agent**. Streaming / wait states / tools / evidence must be *visible and honest*. Creda already has a live API (Amplify + API Gateway + Lambdas + Qwen on ECS) — do **not** rebuild AgentCore/Cognito/React. Steal the *product lesson*: one polished surface that makes the backend’s work obvious.

Also internalize Cursor’s own bar for agent work: [What we’ve learned building cloud agents](https://cursor.com/blog/cloud-agent-lessons) — verify on the real artifact, don’t fake progress, report blockers honestly.

**Creda mantra (put this in the UI chrome subtly if it fits, never as a marketing hero):**
> Good design speaks first.  
> Frontend sells the backend.

---

## Operating procedure (mandatory)

### Phase PLAN — `/architect`
1. Ground: read `docs/CREDA_DESIGN_PHILOSOPHY_FOR_GEMINI.md`, `docs/CREDA_UI_LLM_BUILD_SPEC.md`, current `frontend/index.html`, `frontend/amplify.yml`.
2. Preflight Amplify + API (see below). Stop and report if health fails — **no mocks**.
3. Research every kit URL in the Inspiration Index (open / fetch / skim docs). Produce a short **kit decision table**: Use · Moodboard-only · Skip — with one sentence why, mapped onto Creda surfaces (intake / wait / ruling / exhibits / orders).
4. Sketch the information architecture as **Ruling + Exhibits** (not a chat dump, not a landing page). Types/modules: intake state, poll loop, block renderers, stamp, exhibit slip, orders, chips, evidence dock.
5. Exhaust design space lightly: at least **two** visual directions for the judgment shell (e.g. soft glass case-file vs denser paper dock) — then pick one and proceed.

### Phase BUILD — `/poteto-mode`
- Experience first, prove it works, subtract before you add, smallest vanilla surface that still looks premium.
- Hand-port kit *patterns* into one Amplify HTML file — **not** `npm install` of React kits.
- Verify against live network + acceptance H1–H8 before claiming done.

---

## Product (non-negotiable)

| Field | Value |
|-------|--------|
| Surface | **Tool** — single case workspace |
| Not | Marketing landing, dashboard, charts playground, ChatGPT clone |
| User | Job seeker (India-first) about to pay a fee or share IDs |
| Task (&lt;60s) | Paste → understand risk + **why** → know next action |
| Result model | **Ruling + Exhibits** |

**Always on:** ruling stamp + consequence · 2–4 exhibit slips (They said / We checked / Result / Tier / source) · 2–3 orders · ≤3 follow-up chips.  
**One tap:** “Creda explains its judgment” · full evidence dock.  
**Wait:** stage rail Intake→Evidence→Verdict→Judgment→Follow-up · real evidence as it lands · elapsed timer · stream panel (`agentStreamText`) in mock-browser chrome · **never** blank spinner 60–120s.

**Verdict honesty:** never “verified authentic offer.” High risk → don’t pay / don’t share IDs. Unverified → gaps + follow-ups.

---

## Live stack (Amplify — check / get what you need)

| Item | Value |
|------|--------|
| API | `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com` |
| Amplify | `creda-mvp` · `https://main.d32sg54oqu2gcb.amplifyapp.com` |
| Source | `frontend/index.html` |
| Build | `frontend/amplify.yml` sed-bakes `VITE_API_URL` → `__CREDA_API_URL__` |

**Preflight (must pass):**
```bash
curl -sS "https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com/health"
# expect HTTP 200, status ok, dataReady true
```
Also confirm Amplify env has `VITE_API_URL` set to that API base. If missing, **report** — do not invent a fake “Live API unavailable” badge without a real failed `/health`.

**Wire only live endpoints:** `GET /health`, `POST /cases`, `GET /cases/{id}` + `X-Case-Token`, `POST .../followup`, `POST /reports/scam`. Token → memory + `sessionStorage` only. Escape all dynamic text.

---

## Inspiration Index — research ALL, then consolidate

### UI kits / patterns (open each, decide Use / Moodboard / Skip)

| URL | Creda decision |
|-----|----------------|
| https://21st.dev/magic-chat?source=header&step=project-type | Moodboard — composition ideas only |
| https://www.cult-ui.com/ | Moodboard — taste; hand-port sparingly |
| https://www.neobrutalism.dev/docs/chart | **SKIP** — no charts |
| https://tweakcn.com/editor/theme?utm_source=shadcnblocks | **USE** — theme tokens |
| https://ui.rechesoares.com/docs/flip-card | **USE** — exhibit front/back only |
| https://www.reactbits.dev/text-animations/split-text | **SKIP** — no looping split-text |
| https://ui.lukacho.com/components/mock-browser | **USE** — wait / stream chrome |
| https://animata.design/docs/bento-grid | **USE** — exhibit grid |
| https://www.ui-layouts.com/components/liquid-glass | **USE** — soft glass on judgment shell only (readable text) |
| https://dev.to/kohtet_gintoki/15-re-usable-ui-component-libraries-with-framer-motion-25p9 | Moodboard — pick motion *ideas*, not Framer dumps |
| https://www.unicorn.studio/ | **SKIP** — no WebGL backgrounds |
| https://uiverse.io/ | Moodboard — one button/chip pattern max |
| https://codepen.io/ | Moodboard — one pattern max |
| https://ai-sdk.dev/elements (Vercel AI Elements: Suggestions / Reasoning / Sources / Task / Branch) | **USE patterns** — chips, why disclosure, stage/task status — not full React install |
| https://lightswind.com/ | Moodboard — motion taste |
| https://coss.com/origin | **USE** — Input / Button / Badge / Alert / Accordion / Stepper feel |
| https://nextbunny.co/ | Optional design canvas only — not runtime |
| https://kokonutui.com/ | **USE** — shimmer / entrance motion taste |
| https://reactnativereusables.com/docs | **SKIP** — wrong platform |

### SVG / imagery (artistic, not stocky)

- https://simpleicons.org/ — tiny mono brand marks on demos (Gmail / WhatsApp etc.)
- https://www.vectorlogo.zone/
- https://www.svgrepo.com/ — primary icon set (shield, mail, alert, check, link, chevron) — **stroke icons, not emoji**
- https://webutility.io/image-to-svg-converter — only if converting a needed asset
- https://undraw.co/illustrations — **≤1** empty-state illustration that resonates (case file / shield / inbox) — not a hero collage
- https://www.softr.io/blog/free-svg-illustrations — optional extras

**Images:** add 1–2 quiet illustrations / SVG scenes that reinforce *trust under stress* (case file, shield, careful reading). Never stock “happy corporate handshake.” Prefer inline SVG.

### Visual craft bar
Polished, artistic, visually stunning **and** job-done: warm paper (`#f3f1ec`), ink `#0f2433`, risk `#b42318`, safe `#087443`, warn `#9a6700`, blue `#155eef`. Purposeful motion (exhibit slip-in, stamp land, one urgent pulse, stream shimmer). `prefers-reduced-motion` → instant. **Not** a basic Bootstrap form. **Not** a Tailwind marketing landing.

---

## Forbidden (reject your own work)

- Marketing hero (“A calmer second opinion…”, feature grids, brand manifesto)
- Fake “Live API unavailable” without a real failed `/health`
- Charts, Unicorn WebGL, looping split-text, nested card soup
- Mocks / fake verdicts / hardcoded caseIds
- Claiming verified authentic offer
- Opening a GitHub PR unasked
- `alert()` for normal errors; logging offer text or tokens

---

## Build sequence

1. `/architect` kit table + IA sketch + pick judgment-shell direction  
2. Wipe marketing chrome; blank product shell (intake + idle stage rail)  
3. Live case loop (create / poll / follow-up / report / health)  
4. Ruling + Exhibits result shell + all `BLOCK_RENDERERS`  
5. Craft pass: tokens, bento, glass, flip exhibits, mock-browser stream, SVG icons, one Undraw max  
6. Prove: network tab → real `ap-south-1` host; Amplify bake of API URL; acceptance H1–H8 from `CREDA_UI_LLM_BUILD_SPEC.md`

---

## Done means

A judge opens Amplify, pastes the fee-scam demo, watches **real** evidence arrive, gets a **ruling stamp + exhibit slips** that explain *why*, can follow up — craft (glass / bento / motion / SVG) serves comprehension. Zero marketing-landing look. Zero mocks.

**Start now with `/architect` (research kits + health + sketch). Then `/poteto-mode` and rewrite `frontend/index.html`.**
