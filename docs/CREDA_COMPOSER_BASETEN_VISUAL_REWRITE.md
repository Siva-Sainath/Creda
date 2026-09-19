# COMPOSER — BASETEN-LEVEL VISUAL REWRITE (hard fail if still bland)

**Modes (mandatory):** `/architect` then `/poteto-mode`

You are not allowed to ship another “structure patch.” The human and Grok Bot have rejected multiple deploys that still look like a generic paper/glass SaaS form. **This iteration is a VISUAL PRODUCT REWRITE of `frontend/index.html`.**

Live must change: https://main.d32sg54oqu2gcb.amplifyapp.com/  
API (keep working): https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com  
Vanilla Amplify HTML/CSS/JS + GSAP OK. No React/npm kits. No PR unless asked. Deploy so hard-refresh shows the new look.

## Hard fail / rejection (task FAILED if any true after deploy)
1. Hard-refresh still feels like the same bland tool (marketing H1 + soft glass + stock illustration + paperclip composer).
2. No **obvious** motion language (page load, wait stages, stamp, exhibit stagger) — static labels alone do not count.
3. Telegram CTA is a fat wide button/link eating the aftercare row (must become a compact icon+short label chip).
4. Wait still jumps folder → result in ~2s with no visible intermediate scenes.
5. Follow-up still throws `evidence is not defined` or shows no Creda reply.
6. You only renamed classes / moved buttons without rewriting layout, type, surfaces, and motion.

**Pass bar:** Someone who saw yesterday’s UI says “this is a different product.” Reference craft feel (not clone): https://www.baseten.co/ — one visual system, decisive type, motion that matches the work, accent used sparingly, telemetry mono, no bolted marketing.

---

## /architect (do first — write it in your reply)
Deliver a short design system BEFORE coding:
- Type: display size for H1, mono for stamps only
- Surfaces: paper `#F3F1EC`, hairline dashed construction grid, flat/near-flat cards (radius ≤8px), soft glass on **one** judgment shell only
- Motion list with durations (load / wait scenes / stamp / exhibits)
- Telegram: **compact** icon chip (max ~140px wide), not a banner
- Wireframes: Intake / Wait / Result

Then `/poteto-mode` and **rewrite** the CSS + major markup sections. Prefer delete+rebuild of intake + wait chrome over tweaking.

---

## Visual rewrite requirements

### Intake (must not look marketing)
- Kill stock “doc + magnifier + shield” hero illustration OR replace with one quiet SVG case-file motif ≤120px, not a second column of marketing art.
- Single-column tool focus: H1 short, one lede line, **composer is the hero**.
- Composer = 21st.dev Input Bar pattern: tall NL field, **circular +** attach (not paperclip-only), drag-drop overlay, primary Check.
- Demo chips small/secondary. Channel chips optional and quieter.
- Optional tiny Telegram icon in topbar (icon only + tooltip), not a paragraph CTA.

### Wait (must be animated storytelling)
Even if API returns in 2s, play a **compressed choreography** so humans see it (min dwell ≥700ms/scene, total wait UX ≥2.8s unless reduced-motion):

| Scene | FROM | ANIMATION LOOK |
|-------|------|----------------|
| 1 Folder | CredaShieldArt / SVG Repo | Message sheet **slides into folder**; tab **pulses once**; GSAP |
| 2 Evidence | animata bento + magnifier SVG | Slips **stagger from right** 80ms; magnifier **drifts** yoyo; checks pop |
| 3 OCR | scan-line | Scan **loops** only if attachment |
| 4 Stream | lukacho OR 21st Safari mock-browser + kokonut shimmer | Real browser chrome + `creda://case/{id}/stream`; **sheen on new tokens**; live stream text |
| 5 Stamp | stamp SVG | **One press** (scale down/up, 1.5° tilt) then result |

Stage rail animated: only one active; progress line fills. Signal bars secondary. Copy human (“Checking official sources…”). Never leave “Creda is judging…” as primary.

### Result (must feel stamped case board)
- Big **ruling stamp** (not a tiny RISK pill): HIGH RISK / NOT ENOUGH PROOF / NO CONFLICT — stamp slam once.
- Consequence line.
- E1–E4 **bento slips** (animata): They said / We checked / Result / Tier — stagger in; flip = “Why we trust this” with **real text** or hide the line.
- Orders panel; Need from you / Ask Creda (Ask chips **send**).
- Aftercare: `Check another` · compact Telegram chip · `Report` text link that expands panel. **Telegram must not dominate width.**

### Brand
- New Creda shield SVG mark (memorable at 28px).
- AWS: tiny `Infra · AWS` text/link — never a fat badge.
- Remove bland overlapping dashed footers / debug chrome.

### Motion grammar (Baseten-like: purposeful, continuous where needed)
- Page load: topbar + composer fade-up 400ms ease `cubic-bezier(.22,1,.36,1)`.
- Wait scenes: crossfade 250ms + entrance motion above.
- Exhibits: stagger 60–100ms.
- `prefers-reduced-motion`: static finals, no loops.

### Keep working
- Live API create/poll/followup/report/upload.
- Fix follow-up `evidence is not defined`; always send `X-Case-Token`.
- Fee-scam demo still high_risk.

### SKIP
Unicorn WebGL, looping split-text heroes, chart kits, blank spinner, marketing feature grids.

Tokens: `--ink #0F2433; --muted #5F6D7A; --bg #F3F1EC; --panel #FFF; --line #D7E0E8; --blue #155EEF; --risk #B42318; --safe #087443; --warn #9A6700;`

## Done checklist (reply with all)
1. `/architect` system summary  
2. What you **deleted** from the old intake  
3. Motion you added (list)  
4. Amplify deployed + hard-refresh note  
5. Screenshot descriptions: intake / wait mid-sequence / result  
6. “Ready for Grok Bot test loop”

If you cannot make it look different, say so — do not ship another same-look patch.
