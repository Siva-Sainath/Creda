# COMPOSER — Kill cream grid · real glass · Baseten hero · Stitch-style flow bg

**Modes (mandatory):** `/architect` then `/poteto-mode`

Live: https://main.d32sg54oqu2gcb.amplifyapp.com/
API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
Edit `frontend/index.html` (vanilla + GSAP OK). Deploy Amplify. No PR unless asked.

## Why the human still hates it
The "creda-baseten" theme is the wrong takeaway from baseten.co:
- It paints a **24px construction grid** on cream (`linear-gradient` 1px lines, `background-size: 24px 24px`)
- It **turns OFF glass** (`backdrop-filter: none` on `.glass` / `.liquid-glass`)
- It **shrinks** the tool (`max-width: min(720px, …)`), so buttons/chips feel tiny on a big monitor

Baseten's real craft = decisive headline, generous space, continuous brand motion, one system.
Google Stitch / modern AI canvases = ambient **flowing** backdrop (mesh + soft vector blobs), glass panels floating on top — not graph paper.

**This pass must look obviously different on hard-refresh.**

---

## Hard fail if any true after deploy
1. Cream **construction grid** still visible (any 24px / dashed paper grid on `body`).
2. Glass still disabled (opaque flat cards with no blur over a living background).
3. Layout still capped ~720px with tiny chips/buttons while the rest of the screen is empty.
4. No **rotating / cycling** tagline line under the H1.
5. Background is static cream with no flowing motion (or only a barely-visible mesh).
6. Follow-up / API regressions (`evidence is not defined`, missing `X-Case-Token`).

---

## /architect (write first)
Design system before code:
1. **Kill** `body.creda-baseten` grid theme entirely (or delete the class + CSS block).
2. **Atmosphere:** cream/ink base + animated mesh + SVG flow layer (Stitch-like ambient).
3. **Surfaces:** real glass (`backdrop-filter: blur(16–28px)` + translucent white) on composer, judgment shell, exhibit slips — glass ONLY works if the bg is colorful/moving behind it.
4. **Scale:** use the viewport — hero + composer centered but roomy (`max-width` ~880–960px for tool column; topbar full-bleed feel). Primary Check button tall (≥48px). Chips ≥36px tall.
5. **Hero copy:** short product H1 + rotating promise line (Baseten-style presence, still a tool not a marketing landing).
6. Wireframes: Intake (hero + glass composer) / Wait / Result.

Then `/poteto-mode` and implement.

---

## Build recipe (how to implement — researched)

### 1) Delete the cream grid
Remove from CSS/HTML:
- `body.creda-baseten` rules that set
  `background-image: linear-gradient(...1px...), linear-gradient(...1px...); background-size: 24px 24px;`
- Any other paper/dot construction grids on the page chrome
- Rules that force `backdrop-filter: none` on glass

Do **not** replace the grid with another dashed blueprint look.

### 2) Living background = mesh + SVG flow (Stitch / modern AI sites)
**Layer A — CSS mesh (GPU-cheap):** 3–4 `radial-gradient` ellipses (blue / teal / sage at low opacity) on `body`, animate with `@keyframes` drifting `background-position` ~16–22s ease-in-out infinite (already partially present as `meshDrift` — make it **visible**, not timid).

**Layer B — SVG flow (the "cool vector" feel):** fixed `position: fixed; inset: 0; z-index: 0; pointer-events: none;` SVG with:
- 2–3 soft blurred `<circle>` / organic blobs (fill Creda blue/teal/sage at 8–14% opacity)
- GSAP or CSS `transform` translate/scale yoyo 12–20s
- Optional: one soft path with `stroke-dashoffset` draw (very low contrast)
- Optional light `feTurbulence` + `feDisplacementMap` on a single blob only (keep scale small for perf)
- `prefers-reduced-motion: reduce` → freeze at a pleasant frame

**Layer C — content** `z-index: 1+` with glass panels so blur reads the motion underneath.

References to match *feel* (not clone pixels):
- https://www.baseten.co/ — big decisive type, space, continuous polish
- https://stitch.withgoogle.com/ — ambient AI-canvas atmosphere
- Technique: CSS mesh + glass over mesh (common 2026 SaaS pattern); SVG blob drift without WebGL

**SKIP:** Unicorn WebGL, heavy Three.js, looping split-text heroes, marketing feature grids.

### 3) Glassmorphism (put it back and make it honest)
```css
.glass {
  background: rgba(255,255,255,.62);
  backdrop-filter: blur(22px) saturate(1.6);
  -webkit-backdrop-filter: blur(22px) saturate(1.6);
  border: 1px solid rgba(255,255,255,.75);
  box-shadow: 0 12px 40px rgba(15,36,51,.08), inset 0 1px 0 rgba(255,255,255,.9);
  border-radius: 16px; /* composer can be 20px */
}
```
Apply to: composer shell, wait panel, judgment shell, exhibit cards.
Judgment shell can be the strongest glass. Do not glass the entire page into mud.

### 4) Use the screen (Baseten-scale chrome)
- Intake vertical rhythm: more padding top; H1 ~ clamp(2.2rem, 5vw, 3.25rem), tracking tight
- Lede one line, muted
- **Rotating tagline** under H1 (required): fixed stem + cycling word/phrase, e.g.
  - stem: `Spot `
  - cycle every ~2.8s with fade/slide: `fee-before-job scams` → `fake recruiter domains` · `Telegram offer traps` · `screenshot job pitches` · `"too good" remote roles`
  - Implement with a small JS rotator or CSS; keep `aria-live="polite"`; respect reduced-motion (show first phrase only)
- Composer is the hero: min-height comfortable, textarea ~1.05–1.1rem type, circular **+** attach ≥44×44, primary Check ≥48px height / padding `.85rem 1.4rem`, font-weight 650
- Demo chips larger hit targets; Telegram aftercare stays a **compact** chip (~140px), not a fat card
- Widen tool column; stop the lonely empty margins that make UI feel miniature

### 5) Keep product truth
- Still Ruling + Exhibits tool (not a SaaS marketing landing with feature bento walls)
- Wait storytelling + stamp + exhibits stay
- API: create/poll/followup/report/upload; always `X-Case-Token`; fix `evidence is not defined`
- AWS: quiet `Infra · AWS` micro-line, not a fat badge

---

## Done checklist (reply with all)
1. `/architect` summary
2. Confirmed **deleted** `creda-baseten` grid + glass-kill rules
3. Described mesh + SVG flow layers
4. Rotating tagline phrases list
5. Button/chip size targets you hit
6. Amplify deployed + hard-refresh note
7. "Ready for Grok Bot test loop"

If the cream grid remains, the task failed — do not ship.
