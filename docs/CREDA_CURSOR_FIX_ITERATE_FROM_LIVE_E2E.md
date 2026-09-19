# Cursor fix — live Amplify E2E (ITERATE) · full UI craft

**Modes (mandatory):** `/architect` first, then `/poteto-mode`.

Live UI: https://main.d32sg54oqu2gcb.amplifyapp.com/  
API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com  
Edit: `frontend/index.html` (+ `amplify.yml` if bake needed). Vanilla only. No PR unless asked.

Grok consumer test = **ITERATE**. Site works on a real API but still feels generic. This pass must fix product bugs **and** raise craft to a cohesive case-file tool (Baseten-level gel, Creda paper/ink — not a SaaS marketing hero).

Also read if present: `docs/CREDA_CURSOR_ITERATE_GROK_VERIFY_LOOP.md`, `docs/CREDA_CURSOR_FIX_FROM_LIVE.md`, `docs/design/resources.md`, `docs/CREDA_FIGMA_MAKE_PROMPT.md`.

---

## /architect (before code)

Design package for this iteration only:

1. Follow-up = real Q&A thread (not headline mutation).
2. Chip taxonomy: **Need from you** vs **Ask Creda**.
3. Result aftercare: Check another · Report missed scam · CredaShield Telegram.
4. Wait = SVG stage machine (one active scene) bound to poll.
5. Result = Ruling stamp + Exhibits board (not generic cards).
6. Brand strip: Creda mark + quiet AWS micro-line (no debug footer as brand).

Exhaust 2 options for wait storytelling and result board if needed, pick one, then `/poteto-mode`.

---

## /poteto-mode — implement

### 1) P0 Product bugs
- Follow-up: chip under Ask Creda **sends** (or one-tap send). After `POST /cases/{id}/followup` 202, render user bubble + Creda reply from poll/response. `#conversation-host` must not stay empty. Fix glyph clipping in the input.
- Split chips: Need from you (URL/employer) vs Ask Creda (questions).
- **Report field IA:** remove dashed floating footer composer. Put **Report a missed scam** in **result aftercare** (ghost/text control → expands inline panel with textarea + Cancel/Send). Prefill case excerpt OK. Keep `POST /reports/scam` (or live path) wired.
- Telegram CTA in aftercare + subtle chrome: `https://t.me/CredashieldBot`. Setup: Notion Hackathons playbook / `docs/TELEGRAM_SETUP.md`.

### 2) Loading / wait — resource → component → how it should LOOK

Hand-port into vanilla SVG/CSS/GSAP. **Do not npm-install React kits.** One primary scene visible at a time; stage rail is the source of truth.

#### Master map (use these sources)

| Process (poll) | Take this component FROM this resource | What the user should SEE (animation look) |
|----------------|------------------------------------------|-------------------------------------------|
| **1. Intake / queued** | Stroke icons from **SVG Repo** / Lucide-like paths + light **CredaShieldArt** folder motif (`docs/design/resources.md`) | Message sheet **slides down into a case folder** (Y 12→0, fade 0→1, 400ms `cubic-bezier(.22,1,.36,1)`). Folder tab **pulses once**. Label: “Opening your case…” |
| **2. Evidence gathering** | Slip cards = paper panels; grid rhythm from **animata bento** (structure only) | 2–3 **exhibit slips slide in from the right** staggered 80ms as `evidence[]` grows. A **magnifier SVG drifts** slowly over the top slip (±6px, 2.4s yoyo). Tiny **check ticks** pop on each slip. Label: “Checking official sources…” |
| **3. OCR / screenshot** (only if attach) | Image frame + scan line (CredaShieldArt scan / custom SVG) | Attached image sits in a rounded frame; a **horizontal scan-line sweeps top→bottom in 1.2s loops** while OCR active, then stops. Label: “Reading your screenshot…” |
| **4. Stream / agent writing** | **lukacho mock-browser** tab chrome **or** **21st.dev Safari (ruixen.ui)** mock browser — hand-port HTML/CSS | Fake window: traffic lights + URL `creda://case/{id}/stream`. Body text streams; on each new token a **kokonut-style shimmer** (soft gradient sheen 600ms) across the last line only. Cursor blink. Never mid-word CSS overflow clips. |
| **5. Judgment / stamp warm-up** | Stamp SVG (CredaShieldArt / custom) | Stamp rises above pad (scale 0.92→1.02→1), ink shadow softens; when `agentStatus=READY` **one firm press** (80ms down, 200ms settle, 1.5° tilt). Label: “Writing the ruling…” → then transition to result. |
| **6. Stage rail** | Stepper feel from **coss / origin**-like steps (hand CSS) | Five labels: Intake → Evidence → Verdict → Judgment → Follow-up. Only one `active` (ink underline + filled dot). Completed = check. **Never** show LIVE + COMPLETED + STREAMING together. |
| **7. Signal rack** (secondary) | Simple CSS bars (existing signal-rack OK) | 6–8 bars **breathe** at low opacity behind the scene — telemetry, not the hero. Pause when case COMPLETED. |

#### Motion grammar (all wait scenes)
- Easing: `cubic-bezier(.22, 1, .36, 1)` for entrances; linear only for scan-line.
- Duration: entrances 300–500ms; loops only for scan + gentle magnifier drift + shimmer on new tokens.
- GSAP 3 already allowed per `docs/design/resources.md` — use for stage swaps + stamp press; CSS for shimmer/scan if simpler.
- `prefers-reduced-motion: reduce` → snap to final frame of current stage, no loops.

#### Explicit SKIP while loading
- **reactbits split-text** looping hero — skip on wait (intake optional once, not looping).
- **unicorn.studio / uiverse** WebGL candy — skip.
- **neobrutalism chart** — skip on wait (optional thin confidence bar on **result** only).
- Full-page spinners, skeleton that never binds to poll fields.

#### Bind scenes to real poll fields
Map roughly: `QUEUED`→scene1; evidence growing / `RUNNING`→scene2; screenshot/OCR progress→scene3; `agentStreamText` / STREAMING→scene4; near-ready / READY→scene5 then result view. If total time &lt;3s, play a **compressed** 1→2→5 sequence (still readable), don’t flash empty “exhibits will slip in.”

### 3) How to present results — resource → component → look

| UI block | FROM resource | How it should LOOK |
|----------|---------------|--------------------|
| Judgment shell | **ui-layouts liquid-glass** (soft only) | One frosted panel behind stamp+consequence; readable ink; no heavy blur candy |
| Ruling stamp | Custom SVG + risk/safe/warn tokens (**tweakcn**-style `:root` tokens) | Stamp lands once (same press language as wait). Headline + one consequence under it |
| Confidence / counts | Thin CSS bar OK (**neobrutalism chart** idea only as a **bar**, not a chart page) | Mono micro labels `CONF` `EXHIBITS` `T1/T2` |
| Exhibit grid | **animata bento-grid** | 2–4 slips, uneven spans OK; stagger in 60–100ms |
| Exhibit provenance | **ui.rechesoares flip-card** | Tap flips to “Why we trust this” (plain label — never “FLIP FOR PROVENANCE”) |
| Orders | **coss**-like buttons | Primary/ghost; high-risk top order sticky once on mobile |
| Need / Ask chips | **21st.dev Input Bar** chip row patterns / AI-elements-like chips | Two labeled rows; Need vs Ask |
| Composer (intake) | **21st.dev Input Bar (serafimcloud)** | NL textarea + circular + + drag-drop; glass optional |
| Aftercare Report | Expand-in-place panel (keep dashed style if desired **inside** aftercare, not footer orphan) | Ghost “Report a missed scam” → textarea + Send |
| Telegram | **Simple Icons** Telegram glyph | “Open CredaShield on Telegram” → `https://t.me/CredashieldBot` |

Empty exhibits: hide empty bento; one calm still-unclear line + Need chips. Humanize titles; dedupe. Never “verified authentic offer.”

### 4) UI enhancement — kill generic chrome
- Stronger **Creda shield** SVG mark (readable at 24–32px); wordmark + quiet product label. Soft-pedal or remove “Verify before you trust” marketing hero energy on the tool chrome.
- Background: warm paper `#F3F1EC` + light construction grid or soft mesh — cohesive, not stock Tailwind hero.
- **AWS:** quiet micro-line `Infra · AWS ap-south-1` + small official-style mark OR text only. Remove muddy homemade smile as primary brand. Keep API health separate.
- Remove customer-facing debug: `session-only tokens`, lowercase `creda` status pill as brand, overlapping dashed footers.
- Type: Plus Jakarta / similar for UI; JetBrains Mono for stamps/telemetry. One spacing rhythm (8px).
- Primary CTA ink/blue once; state colors only for risk/safe/warn.
- Optional ≤3 demo chips that **fill NL composer** then hit real API (fee scam / clean careers / vague recruiter).

### 5) Tokens (keep consistent)
`--ink #0F2433; --muted #5F6D7A; --bg #F3F1EC; --panel #FFF; --line #D7E0E8; --blue #155EEF; --risk #B42318; --safe #087443; --warn #9A6700;`

---

## Done
Reply: `/architect` decisions · `/poteto-mode` files changed · P0/P1 done · “Ready for Grok Bot test loop”.

Do not claim SHIP. Human will say **run that entire test loop**.
