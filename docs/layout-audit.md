# Creda layout audit (pre-redesign)

**Scope:** Identify every CSS/markup constraint that produces the narrow “single-card” desktop layout.  
**Build under audit:** `baseten-20260919-58-single-card` (`frontend/index.html` meta + live Amplify).  
**Measured live @ 1440:** `.shell` = **720×1006**, **360px** empty gutter each side (`docs/design-research.md`).

No layout code was changed for this document.

---

## 1. Root cause (smoking gun)

| File | Line(s) | Constraint | Effect |
|------|--------:|------------|--------|
| `frontend/styles.css` | **1409** | `body.creda-v58 .shell { max-width: 720px; margin: 0 auto; }` | Caps **entire app chrome** at 720px and centers it. Overrides earlier `--col` / `--col-wide` (~1360–1400px). |
| `frontend/index.html` | **14** | `<body class="creda-baseten creda-v58">` | Activates the v58 ruleset that applies the 720px shell. |
| `frontend/index.html` | **8** | `creda-build` = `…-58-single-card` | Tags the intentional single-column intake rewrite. |

**Live confirmation (CDP @ 1440):** `shell.maxW = 720px`, `shell.left = 360`, `sideGutterPx = 360`.

---

## 2. Width / centering constraints (active cascade)

### Tokens (still defined, partially defeated by v58)

| File | Line(s) | Rule | Notes |
|------|--------:|------|-------|
| `styles.css` | 22–23 | `--col: min(1360px, calc(100vw - 3rem))` | Intended wide column; **shell 720 wins** for layout. |
| `styles.css` | 23 | `--col-wide: min(1400px, calc(100vw - 3rem))` | Used by baseten main/topbar, but nested inside 720 shell. |

### Global shell / main / topbar / footer

| File | Line(s) | Rule | Notes |
|------|--------:|------|-------|
| `styles.css` | 79 | `.shell { min-height: 100vh; display: flex; flex-direction: column; }` | Full height OK; no width until v58. |
| `styles.css` | 80–82 | `.topbar { max-width: var(--col); margin: 0 auto; width: 100%; … }` | Centered column (legacy). |
| `styles.css` | 260–262 | `main { max-width: var(--col); margin: 0 auto; padding: 0 1rem 3rem; }` | Centered column (legacy). |
| `styles.css` | 1053 | `.footer { max-width: var(--col); margin: 0 auto; … }` | Same. |
| `styles.css` | 1080–1086 | `body.creda-baseten .topbar/main/footer { max-width: var(--col-wide); }` | Widens to ~1400 **inside** shell; irrelevant while shell is 720. |
| `styles.css` | 264–269 | `body.view-bleed` / `view-wide` widen main/topbar/footer | `app.js` toggles `view-wide` on wait/result; still trapped by shell. |

### v58 single-card block (primary)

| File | Line(s) | Rule | Notes |
|------|--------:|------|-------|
| `styles.css` | 1409 | `.shell { max-width: 720px; margin: 0 auto; }` | **Must remove/replace in Step 3.** |
| `styles.css` | 1410 | `.intake-single { display: grid; gap: 1rem; }` | One-column intake stack. |
| `styles.css` | 1418–1420 | `.composer-card` bordered card | Fine as a **pane** surface; not the page width bug. |
| `styles.css` | 1426–1428 | `textarea { min-height: 148px }` | Fixed height; Step 3 wants grow-to-fill pane. |
| `styles.css` | 1495 | `.explain-svg { max-width: 320px }` | Decorative cap OK. |
| `styles.css` | 1519 | `#stage-svg { max-width: 420px; margin: 0 auto }` | Centers wait art in narrow column. |

---

## 3. Earlier layouts vs current “single-card”

| Era | Marker | Layout intent | Status in tree |
|-----|--------|---------------|----------------|
| Pre-baseten | `.intake-shell` two-col @ 960px (`styles.css` ~270–275) | Left composer / right secondary | Still in CSS; **not used** by v58 markup (`intake-single` instead). |
| Baseten craft | `body.creda-baseten` + `--col-wide` + `.intake-shell` grid @ 960 (`1244–1250`) | Wider stitch-like split | Markup removed aside/drop-panel; CSS remains as dead path. |
| v58 single-card | `creda-v58` + build tag | One composer card, no right tombstone, Telegram visible | **Live.** Fixed the tombstone UX but **regressed viewport use** via 720 shell. |

**Difference that matters:** Earlier builds constrained **content** to ~1360–1400px. v58 constrained the **whole `.shell`** to 720px — a step backward for desktop product density.

---

## 4. Markup structure (current)

File: `frontend/index.html`

| Lines | Structure | Layout implication |
|------:|-----------|-------------------|
| 15–35 | `.shell` > `.topbar` | Topbar width = shell = 720 |
| 37–99 | `#view-intake` > `.intake-single` | Vertical stack only |
| 46–64 | `#composer-shell.composer-card` | Single card; drop target |
| 69–72 | `.demo-chips` | Under card |
| 74–86 | `#telegram-row` | Stacked card, not side strip |
| 101–149 | `#view-wait` > `.wait-single` | Same narrow column |
| 152–177 | `#view-result` > `.result-board` | Same narrow column; follow-up inside board |
| 188–198 | `#report-sheet` | Overlay (OK to keep centered) |

**Missing for Step 3 target:** No left/right pane wrappers; wait and result are separate full-main sections, not a persistent right “case file” pane.

---

## 5. JS layout coupling (do not break IDs)

| File | Line(s) | Behaviour | Constraint note |
|------|--------:|-----------|-----------------|
| `app.js` | 789–790 | Removes `view-bleed`; sets `view-wide` on wait/result | Width helpers; harmless once shell is full-bleed. |
| `app.js` | (wireComposer, render*, WaitStoryboard) | Depends on IDs: `composer-shell`, `offer-text`, `btn-check`, `attachment-row`, `telegram-row`, `view-*`, `ruling-host`, `followup-input`, `report-sheet`, … | Step 3 may **wrap** nodes; must **keep IDs/handlers**. |

---

## 6. Other size caps (secondary; not the gutter bug)

| File | Line(s) | Rule | Keep / rethink |
|------|--------:|------|----------------|
| `styles.css` | 149–150 | Conv bubbles `max-width: 92–96%` | Keep (readability). |
| `styles.css` | 506–509 | `.lede` / copy `max-width: 36rem` | Keep as text measure. |
| `styles.css` | 914 | `.ruling .consequence { max-width: 40rem }` | Keep as text measure. |
| `styles.css` | 1394–1405 | Report sheet `min(520px, 100%)` | Keep; fix responsive sizing only. |
| `styles.css` | 54–55 | `body { min-height: 100vh }` | Prefer `100dvh` in Step 3. |

---

## 7. Checklist for Step 3 (delete / replace)

- [ ] Remove or override `body.creda-v58 .shell { max-width: 720px; margin: 0 auto; }` (line 1409).
- [ ] Make `.shell` / `main` / `.topbar` full-bleed with fluid gutters; apply max-width only to text blocks and optional workspace inner.
- [ ] Introduce desktop two-pane workspace (≥1024); collapse below.
- [ ] Grow `#offer-text` with pane height (not fixed 148px only).
- [ ] Relocate Telegram to slim band or side strip without changing copy/steps.
- [ ] Pin follow-up to bottom of right pane.
- [ ] Preserve all existing IDs, API calls, and GSAP wait storyboard.
- [ ] Copy before screenshots: `docs/screenshots/before/creda-before-1440.png` (+ 390 when captured).

---

## 8. Verdict

The narrow layout is **not** caused by `--col` alone. It is caused by the **v58 shell max-width of 720px** layered on a single-column `intake-single` markup. Earlier baseten CSS already knew how to go wide (`--col-wide`, two-column `intake-shell`); v58 abandoned that for a mobile-first card and never restored a desktop workspace.
