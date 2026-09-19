# UI PACK 2 — styles.css full rewrite

**Prerequisites:** UI PACK 0 + UI PACK 1 done.  
**File:** Replace `frontend/styles.css` entirely (~950–1150 lines).  
**Do not** patch the old 2419-line file — delete and rewrite.

---

## Why rewrite (not prune)

The live file stacks four body-class layers (`creda-baseten`, `creda-v58`, `creda-v62`) with ~600–750 lines of dead CSS and ~25 conflicting rules. HTML now uses `<body class="creda">` only. `app.js` never reads version body classes.

**Critical mobile bug to fix:** old `body.creda-v62 { overflow: hidden }` (line 2151) had no media query — phones could not scroll.

---

## Authoring order (mobile-first)

Write sections in this exact order:

1. `:root` tokens (verbatim block below)
2. Reset + `body.creda` mesh background
3. Utilities (`.hidden`, `.visually-hidden`, `.btn`, `.btn-text`, `.send-btn`, `.error-host`)
4. `.shell`, `.topbar`, `.footer`
5. `main`, `.workspace`, `.pane`, `.glass-pane`, `.glass-panel`
6. Intake: `#view-intake`, `.intake-single`, `.composer-card`, `.composer-toolbar`, `.composer-safety`, `.telegram-chip`
7. Casefile empty: `#casefile-empty`, `.casefile-guide`
8. Wait: `#view-wait`, `.wait-single`, `.prestream-rail`, `.stage-canvas`, `.stage-scene`, `.evidence-slip`
9. Result: `#view-result`, `.result-board`, `.result-toolbar`, `.board-stamp`, `.board-headline`, `.tile-grid-3x2`, `.tactic-tile`, `.action-chip`, `.exhibit-slip`, `#judgment-host`, `.why-collapsed`, `.sticky-urgent`, `.board-thread`, `.followup-composer`
10. Report sheet: `#report-sheet`
11. `@media (min-width: 480px)` — tile grid 2 col
12. `@media (min-width: 768px)` — spacing, toolbar row
13. `@media (min-width: 900px)` — tile grid 3×2
14. `@media (min-width: 1024px)` — two-pane + **desktop-only viewport lock**
15. `@media (min-width: 1440px)` — wider gutters
16. `@media (prefers-reduced-motion: reduce)` — kill animations, force board visible

---

## `:root` — preserve verbatim (from old lines 1–35, plus v62 glass overrides)

```css
:root {
  --ink: #0f2433;
  --muted: #5f6d7a;
  --bg: #f3f1ec;
  --bg-mesh-blue: rgba(21,94,239,.09);
  --bg-mesh-sage: rgba(61,90,69,.07);
  --bg-mesh-teal: rgba(45,168,154,.06);
  --panel: #fff;
  --line: #d7e0e8;
  --line-strong: #c3ced8;
  --blue: #155eef;
  --risk: #b42318;
  --safe: #087443;
  --warn: #9a6700;
  --sage: #e8efe8;
  --sage-ink: #3d5a45;
  --radius: 7px;
  --shadow: 0 1px 0 rgba(15,36,51,.04);
  --shadow-lift: 0 2px 8px rgba(15,36,51,.06);
  --font: "Plus Jakarta Sans", system-ui, -apple-system, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  --ease: cubic-bezier(.22,1,.36,1);
  --risk-bg: #fef3f2;
  --safe-bg: #ecfdf3;
  --warn-bg: #fffaeb;
  --blue-bg: #eff4ff;
  --glass: rgba(255,255,255,.62);
  --glass-strong: rgba(255,255,255,.78);
  --glass-border: rgba(255,255,255,.72);
  --glass-edge: rgba(15,36,51,.08);
  --glass-blur: 18px;
  --glass-shadow: 0 8px 32px rgba(15,36,51,.05), 0 1px 0 rgba(255,255,255,.9) inset;
  --header-h: 3.5rem;
  --workspace-max: min(1760px, 100vw);
  --gutter: clamp(1rem, 2.5vw, 2.5rem);
}
```

---

## Layout contract

### Base (all widths)

```css
body.creda {
  margin: 0;
  min-height: 100dvh;
  overflow-x: hidden;
  overflow-y: auto; /* mobile MUST scroll */
  font-family: var(--font);
  color: var(--ink);
  /* mesh background + meshDrift animation — copy from old lines 54-64 */
}

.shell {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0;
}

.workspace {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  padding: 0 var(--gutter) var(--gutter);
  width: 100%;
  max-width: var(--workspace-max);
  margin: 0 auto;
  min-width: 0;
}

.pane { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
```

### Desktop only `@media (min-width: 1024px)`

```css
body.creda { overflow: hidden; } /* lock ONLY here */
.shell { height: 100dvh; max-height: 100dvh; overflow: hidden; }
main, .workspace { overflow: hidden; flex: 1; min-height: 0; }
.workspace {
  grid-template-columns: minmax(0, 0.42fr) minmax(0, 0.58fr);
  gap: 1.15rem;
  height: 100%;
  padding-top: 0;
}
.pane-intake, .pane-casefile { overflow: hidden; flex: 1; min-height: 0; }
#view-intake,
#view-wait:not(.hidden),
#view-result:not(.hidden),
#casefile-empty:not(.hidden) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
}
```

---

## Component rules (must implement)

| Component | Rule |
|-----------|------|
| `.glass-pane` | `border-radius: 18px`, `backdrop-filter: blur(14px)`, light border `--glass-edge` |
| `.glass-panel` | Stronger glass, `border-radius: 16px` on composer |
| `.topbar` | Full width, frosted `backdrop-filter: blur(16px)`, gutter padding |
| `.composer-card` | `border: 1.5px solid rgba(15,36,51,.12)`, grows on mobile; `@1024` max-height `min(38vh, 320px)` |
| `.composer-toolbar` | `display: flex; justify-content: flex-end; gap: .5rem; flex-wrap: wrap` — **no** `position: absolute` |
| `.composer-safety` | Normal flow below card, `margin: .35rem 0 0`, **no z-index** |
| `.telegram-chip` | `display: inline-flex`, max-width `11rem`, Telegram blue `#229ED9`, min-height `44px` |
| `.send-btn`, `.btn` | min-height `44px` below 768px |
| `.result-toolbar` | `display: flex; justify-content: space-between; gap: .75rem; position: relative; z-index: 2` |
| `.board-stamp-host`, `.board-stamp` | `pointer-events: none` — stamp never blocks clicks |
| `#btn-new`, `.result-toolbar .btn-text` | `position: relative; z-index: 3; min-height: 44px` |
| `.sticky-urgent` | **static** (not sticky) below 1024px; sticky only `@min-width: 1024px` with `z-index: 2` |
| `.followup-composer` | Always `position: relative` in document flow — **never sticky** |
| `#judgment-host` | Inside `.result-board`; `margin-top: .5rem; clear: both` |
| `.why-collapsed` | `margin: .5rem 0; max-width: 100%` — no overlap with tiles |
| `.tile-grid-3x2` | `display: grid; gap: .65rem`; 1 col default, 2 col `@480`, 3 col `@900` |
| `.tactic-tile` | Glass card, icon box 34×34, hover lift `@media (hover: hover)` |
| Scrollbars | `scrollbar-width: thin` on scroll containers only |
| `#casefile-empty` | **Visible on mobile** — compact guide, not `display: none` below 1024 |

---

## Banned selectors (grep must return 0)

```
flip-card
flip-inner
flip-front
flip-back
bento
telegram-band
telegram-row
drop-panel
attachment-gallery
stage-rail
wait-pipeline
demo-chip
intake-shell
pipeline-panel
creda-v2
view-bleed
max-width: 720px
creda-baseten
creda-v58
creda-v62
```

---

## `!important` policy

- **Zero** `!important` in normal rules.
- **Only** inside `@media (prefers-reduced-motion: reduce)` for forcing `.board-stamp`, `.board-headline`, `.tactic-tile` opacity/visibility.

---

## Stamp tones (keep product identity)

```css
.board-stamp.risk .stamp-frame { stroke: #F04438; }
.board-stamp.safe .stamp-frame { stroke: #12B76A; }
.board-stamp.warn .stamp-frame { stroke: #F79009; }
```

---

## Verify (hard-fail)

```bash
cd /Users/siva/Documents/first_commit_hack/frontend
wc -l styles.css                    # expect 900–1200
for s in flip-card bento telegram-band demo-chip creda-v58 max-width:\ 720px; do
  echo -n "$s: "; grep -c "$s" styles.css || echo 0
done
grep -c '!important' styles.css     # count; only in reduced-motion block
```

**Visual checks** (IDE browser or local serve):
- 390px: page scrolls vertically; no clipped content.
- 1024px+: two panes fill viewport; internal pane scroll only.
- No horizontal scrollbar at 390, 768, 1024, 1440, 1920.

---

## Next pack

→ [UI_PACK_3_js_p0_fixes.md](./UI_PACK_3_js_p0_fixes.md)
