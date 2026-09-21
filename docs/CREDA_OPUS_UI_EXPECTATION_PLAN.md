# Creda UI — Opus plan prompt (what Siva actually expects)

**Paste the block below into Opus.** Goal: Opus audits against this vision, then writes a Composer-ready plan. No marketing fluff. No flip cards. Ship a judge-proof tool UI.

---

## COPY TO OPUS

```
You are Opus. Produce a PLAN (not code yet) for Cursor Composer to rebuild Creda WorkOffer Shield’s Amplify UI so it matches the product owner’s iterated expectations below.

Live site: https://main.d32sg54oqu2gcb.amplifyapp.com/
Repo UI: /Users/siva/Documents/first_commit_hack/frontend/  (vanilla index.html, styles.css, app.js)
API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
Current meta often: baseten-20260919-v64-intake-clean — recheck.

After reading live DOM + CSS + this brief, output:
1) Gap analysis (expectation vs live, severity)
2) Information architecture (desktop + mobile)
3) Visual design contract (tokens, density, motion, vectors)
4) Ordered Composer packs with hard-fail checks
5) Verification matrix (desktop 1280×800 + mobile 390×844)

════════════════════════════════════════
WHAT THIS PRODUCT IS (non-negotiable)
════════════════════════════════════════
Creda is a WorkOffer Shield: paste a job offer → get a SCAM / RISK / SAFE ruling with evidence.
It is a TOOL SURFACE for WeMakeDevs judges, not a landing page.

Mental model: case file / shield / VirusTotal-style evidence dashboard.
Qwen (LLM-as-judge) writes the stamp. Tools only gather evidence.
Target task time under 60 seconds to understand a result.

FORBIDDEN forever:
- Flip cards / flip interactions
- Marketing hero, vibe-kit dumps, neon cyberpunk
- max-width ~720px “postcard” shell that wastes the screen
- Selling screenshot/PDF multimodal as if it works when VLM is not live
- Text walls; badge-only results with no “why”
- Stupid arrows (→ ▾) or decorative chevrons in buttons
- Empty “Next step” cards with no content
- PRs unless owner asks

════════════════════════════════════════
OWNER’S ITERATED UI EXPECTATION (the north star)
════════════════════════════════════════

### A. Overall craft
- Professional polish like baseten.co: smooth motion, elements that gel, purposeful — not decorative.
- Glassmorphism used lightly (glass panels, soft borders, blur) — case-file taste, not frosted candy.
- GSAP for wait + reveal (stagger). Respect prefers-reduced-motion → static final frames.
- Customizable SVG / Lucide-or-Heroicons hand-port vectors for wait scenes and tactic tiles — not stock marketing illustrations.
- Full viewport use on desktop. No awkward empty half-page. No cramped one-side layout.
- Zero overlapping controls. Every button in a correct enabled/disabled state.
- No ugly scrollbars / double scroll regions.

### B. Desktop layout (primary judge view)
Two-pane full-bleed (~ElevenLabs / Baseten composer tools):
- LEFT: Intake (composer)
- RIGHT: Wait scenes OR Results board
When idle, right pane can show a calm empty state (shield / “Paste an offer to open a case”) — not a blank void and not a marketing column.
Use 100% width/height of the browser chrome. Gutters small but consistent. No 720px center card.

### C. Intake (left) — what owner demanded after broken builds
1. ONE paste box. Clear placeholder: paste job offer text. Do NOT advertise “drop screenshot/PDF” unless multimodal path is LIVE.
2. NO demo chips (Fee / Kit / preset scam buttons) — judges must paste or use Telegram.
3. NO “+” attach floating over OTP warning. Attach only if multimodal is proven live; otherwise hide.
4. Telegram = ONE compact chip/button:
   - Recognizable Telegram blue
   - Icon + short label (@CredashieldBot or “Open in Telegram”)
   - Accessible (aria-label, keyboard focus)
   - Max ~11rem wide; does not dominate the row
   - Links https://t.me/CredashieldBot
5. Check + Clear with correct states: disabled when empty; locked busy while checking; Clear never fights Check.
6. OTP / safety line NEVER overlaps toolbar buttons.
7. No cramped chip row. Spacing must breathe.

### D. Wait experience (right, while checking)
Low text. Stage playlist with SVG scenes, e.g.:
- Offer received
- Searching official sources (ATS / indexed employers — not fake “googling the web”)
- Weighing evidence
- Stamping ruling
Each scene ≥ ~700ms before advancing. Human labels only (no FILE/QWEN raw codes).
Do not jump early to “Stamping”.
GSAP stagger; optional glass card behind illustration.
If backend is slow (CPU path 50–70s), wait UI must feel intentional, not frozen.

### E. Results board (right) — “Why this is a scam” evidence dashboard
NOT a risk badge alone. Owner rejected flip cards specifically so judges can see why.

Required structure:
1. Physical STAMP (HIGH RISK / SCAM / SAFE / NOT ENOUGH PROOF) — large, legible, never ghosted (opacity stuck is a P0 bug)
2. Plain-language HEADLINE (one line)
3. Short CONSEQUENCE (what the victim loses / next harm) — distinct from headline
4. ≤6 flat EVIDENCE TILES (no flip):
   - Tactic icon (SVG) + short label + 1 smoking-gun fact
   - Source chip when available
5. Action chips (nextActions from API / presentation) — real actions only; never empty shells
6. Follow-up input under the board:
   - Asking a question must NOT wipe the board
   - Must not hang forever on “writing the explanation”
   - Answer appears as a clear reply block; stamp/tiles stay

Stamp must not block “Check another”. Tiles must not overlap why-details.

Inspiration grammar: VirusTotal / Have I Been Pwned style scannable boards — visual, sparse text, source chips.

### F. Mobile (required — currently missing)
Owner expects a real phone layout, not a squashed desktop:
- Single column, full width, no horizontal scroll
- Intake first; after Check, results push below or swap to a results view with clear back / “Check another”
- Stamp + headline + consequence stack; tiles 1-col or 2-col grid without overlap
- Telegram chip + Check + Clear remain tappable (≥44px targets)
- Wait scenes full-width, readable on 390px
- No overlapping OTP/toolbar on narrow screens
Breakpoints: design for ~390 and ~768 as well as 1280.

### G. Honesty about multimodal
Do not UI-lie. If GPU VLM is not live: text-first copy. Telegram photos may be accepted by bot but UI must not claim “upload any screenshot and we’ll parse it” until agentSource proves VLM.

════════════════════════════════════════
KNOWN LIVE UI FAILURES TO PLAN AGAINST
════════════════════════════════════════
P0: ghost stamp/tiles (GSAP opacity); follow-up stuck / board wipe; stamp blocks clicks
P1: early stamp wait; scrollbars; Check enabled in-flight; why-panel overlaps tiles; bare/minimal craft; multimodal copy lies
Layout: button overlap; wasted desktop space; broken formatting
Mobile: not formatted / not rendering as an app — must be fixed in plan
Intake debt: chips/+/Telegram row issues were partially cleaned in v64 — verify and finish

════════════════════════════════════════
WHAT SUCCESS LOOKS LIKE (acceptance)
════════════════════════════════════════
Desktop 1280×800:
- Full bleed two panes, no postcard shell, no large empty void
- Intake clean: paste + Check/Clear + one Telegram chip; no demo chips; no overlapping OTP
- Run fee-scam paste → wait scenes animate → stamp opacity 1 → ≤6 tiles readable → actions work
- Follow-up answers without destroying board
- Hard refresh meta bump after deploy

Mobile 390×844:
- No overlap, no horizontal scroll, usable Check + Telegram
- Results fully readable without pinching
- Same stamp/tiles/actions content as desktop, reflowed

Craft:
- Light glass + GSAP + SVG vectors present and coherent
- Looks like a case-file tool a judge trusts in <60s

════════════════════════════════════════
YOUR OUTPUT FORMAT
════════════════════════════════════════
1. Gap table: Expectation | Live today | Severity | Fix pack
2. Wireframe description (desktop + mobile) in plain text/ASCII
3. Design tokens to keep/add (ink, glass, risk/safe, radii, type scale)
4. Vector inventory (wait scenes + tile icons) + kit choice (Lucide/Heroicons)
5. Composer packs A→N ordered, each with hard-fail verify
6. Out of scope / do-not-claim
7. 90-second judge demo script matching the UI

Work hard. Be concrete. Prefer deletes of bad UI over more decoration.
```

---

## How to use
1. Paste the COPY TO OPUS block into Opus.
2. Optionally attach screenshots of live Amplify + `frontend/*`.
3. Ask Opus: “Plan only first; then emit Composer pack A.”
