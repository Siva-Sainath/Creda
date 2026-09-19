# Cursor prompt — Creda live Amplify craft + IA fixes

**Paste this entire prompt into Cursor Agent** against repo `frontend/index.html` (Amplify live: https://main.d32sg54oqu2gcb.amplifyapp.com/).

**Do not open a GitHub PR unless asked.** Live API only: `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`. Vanilla HTML/CSS/JS + existing GSAP — no React/npm UI kits.

---

## Context / judge notes (live site)

Live site is a **tool** with intake composer, stage rail, signal rack, GSAP stage SVG scenes, ruling + exhibits — good direction, but craft still lags [Baseten](https://www.baseten.co/):

| Area | Problem on live |
|------|-----------------|
| Logo / brand mark | Generic tiny shield SVG — not memorable, weak vs Baseten’s decisive mark language |
| AWS badge | Footer AWS wordmark feels bolted-on; “Powered by AWS” / badge doesn’t gel with paper case-file system |
| Wait storytelling | Stage SVG + signal bars exist but read as decoration; stages don’t clearly narrate *what Creda is doing right now* with icons/copy tied to `agentProgress` / evidence arrivals |
| Results | Ruling + exhibits need tighter stamp → consequence → E1–E4 → orders hierarchy; more “case board”, less stacked cards |
| Report UI | Dashed “Report a missed scam” sits in wrong IA (footer zone) — feels orphaned, not part of the case flow |
| Telegram | No obvious path to **@CredashieldBot** / setup for CredaShield Telegram service |

Baseten craft to steal (tool density, not landing): construction rhythm, flat decisive surfaces, mono telemetry stamps, accent only for state, motion that means “system alive”, one visual language end-to-end.

---

## External resources (use these)

1. **Hackathons playbook (Notion)** — open and mine for UI/SVG/vector links + any Telegram setup notes:  
   https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd  
   (also try https://www.notion.so/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd)

2. **Repo docs**
   - `docs/TELEGRAM_SETUP.md` — bot is **@CredashieldBot** (`https://t.me/CredashieldBot`); BotFather + webhook deploy steps for operators
   - `docs/design/resources.md` — CredaShieldArt inline SVG notes
   - `docs/CREDA_DESIGN_PHILOSOPHY_FOR_GEMINI.md` + `docs/CREDA_UI_LLM_BUILD_SPEC.md` — Ruling + Exhibits contract
   - `docs/CREDA_FIGMA_MAKE_PROMPT.md` — intake = NL only + plus/drag-drop (no Add-details form)

3. **SVG / icon sources (hand-inline, no npm)**  
   Prefer stroke icons from: SVG Repo, Lucide-style paths, Simple Icons (Telegram, AWS smile mark carefully), Undraw ≤1 scene.  
   Kit *patterns* only (hand-port CSS): tweakcn tokens, coss controls, animata bento exhibits, lukacho mock-browser, kokonut shimmer, soft glass on judgment shell only.  
   **Skip:** neobrutalism charts, Unicorn WebGL, looping split-text.

---

## Exact changes required

### 1) Brand mark / logo
- Redesign header `.brand-mark` as a **distinct Creda shield mark** (inline SVG): shield + document/check motif, 2 weights, works at 24px and 40px.
- Wordmark “Creda” + tiny product label “WorkOffer Shield” in mono or muted microtype.
- Optional: favicon from same SVG.
- Must feel intentional on warm paper `#F3F1EC` / ink `#0F2433`.

### 2) AWS presence (fix, don’t delete trust)
- Remove the lonely bolted footer AWS wordmark-as-primary branding.
- Replace with a **quiet infra strip** that gels with the case-file UI, e.g. mono microcopy:  
  `Infra · AWS ap-south-1` + small official AWS smile mark (Simple Icons / AWS brand SVG, correct colors, ~14–16px height) OR text-only if mark fights the palette.
- Optional header health pill already exists — keep API health there; AWS is *provenance*, not a marketing sticker.
- Copy must not scream “Powered by AWS” as a hero. Prefer “Runs on AWS” / “Infra on AWS” in mono.

### 3) Wait / loading = SVG story of what is happening
Drive scenes from live poll fields (`status`, `agentStatus`, `agentProgress`, `evidence[]`, `checks[]`, stream text):

| Stage | SVG story (inline) | User-facing line |
|-------|--------------------|------------------|
| Intake | Envelope / paste → case folder | Opening case file |
| Evidence | Magnifier over domain/ATS slips | Checking official sources |
| OCR / screenshot | Scan line over image frame | Reading your screenshot |
| Judgment | Scale / stamp warming up | Creda writing the ruling |
| Follow-up | Chip / question marks | Waiting on your answers |

Requirements:
- One **active** SVG scene at a time (already have `#scene-intake|evidence|judge|ocr` — tighten art + bind copy).
- Stage rail labels must match the active story; highlight current; checkmarks on done.
- As each evidence item arrives, animate a small **exhibit slip** (title + tier pill) — not only signal bars.
- Stream panel = mock-browser with real `agentStreamText` / progress strings.
- Never blank spinner. Respect `prefers-reduced-motion`.

### 4) Results presentation
- Stamp first (HIGH RISK / NOT ENOUGH PROOF / NO CONFLICT FOUND) + one consequence line.
- Numbered exhibits E1–E4: They said / We checked / Result / Tier / source.
- Orders (urgent sticky on high_risk once).
- Need-from-you chips ≤3.
- One-tap: Why this ruling + full evidence dock.
- Never “verified authentic offer.”

### 5) Move “Report a missed scam” (IA fix)
**Wrong today:** dashed report panel living as an orphan footer block.

**Do this instead:**
- On **result view only**, place Report as a secondary action in the **orders / aftercare row** next to “Check another” (ghost button → expands inline panel or drawer).
- Footer keeps only: quiet AWS infra micro-line + session note — **no** big dashed report box.
- Keep existing `POST /reports/scam` wiring; only relocate UI.

### 6) CredaShield Telegram quick access
Add a clear CTA (intake footer of composer OR result aftercare — prefer **intake trust row + result aftercare**):

- Label: **Check offers in Telegram**
- Link: `https://t.me/CredashieldBot` (open new tab)
- Helper: “Paste a job message to @CredashieldBot — same ruling as the web.”
- Secondary text link for operators: “Set up your own CredaShieldTelegram” → point to in-repo `docs/TELEGRAM_SETUP.md` **if** served, OR Notion playbook section, OR a short in-UI modal with BotFather steps summarized (no secrets). Prefer linking Notion playbook for hackathon judges:  
  `https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd`  
  with anchor text **CredaShieldTelegram setup**.
- Use Simple Icons Telegram glyph (mono) inline SVG.

### 7) Intake reminder (if still form-y)
Composer must stay **natural language + circular + attach + drag/drop**. No Add-details sender/employer/links fields.

---

## How to open & verify (Cursor must do this)

1. `curl -sS https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com/health`
2. Open local baked `frontend/dist/index.html` or Amplify URL after deploy.
3. Run Amazon fee-scam demo → watch wait SVG stages + live exhibits → confirm high_risk stamp + orders.
4. Send one follow-up chip.
5. Confirm Report opens from **result aftercare**, not footer dashed orphan.
6. Confirm Telegram link opens `t.me/CredashieldBot`.
7. Mobile ~390 width smoke.

---

## Definition of done
Judge opens Amplify, feels one cohesive case-file system (Baseten-level gel, Creda paper/ink identity), understands wait via SVG story, gets a clear ruling board, can report a miss from the result flow, and can jump to @CredashieldBot / setup docs — no marketing landing, no bolted AWS sticker, no footer report orphan.

Start by reading live `frontend/index.html`, Notion playbook SVG notes, and `docs/TELEGRAM_SETUP.md`, then implement the seven change groups above.
