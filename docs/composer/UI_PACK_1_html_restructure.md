# UI PACK 1 — index.html restructure

**Prerequisite:** UI PACK 0 committed.  
**Branch:** `creda/mvp-g4dn-ship`  
**File:** `frontend/index.html` only (no CSS/JS in this pack).

---

## Goals

1. Single body class: `creda` (remove `creda-baseten creda-v58 creda-v62`).
2. Move `#judgment-host` inside `.result-board` (fixes overlap without z-index hacks).
3. Add `#scene-careers` SVG for distinct “official careers” wait scene.
4. Remove multimodal UI hints (`#drop-overlay`, `#file-input`, attachment row stays hidden).
5. Rewrite casefile empty copy — no screenshot/PDF promise.
6. Bump meta to `baseten-20260919-v65-ui-rewrite`.

---

## Exact edits

### A. `<head>` — meta bump

**Find:**
```html
<meta name="creda-build" content="baseten-20260919-v64-intake-clean" />
```

**Replace:**
```html
<meta name="creda-build" content="baseten-20260919-v65-ui-rewrite" />
```

### B. `<body>` — class collapse

**Find:**
```html
<body class="creda-baseten creda-v58 creda-v62">
```

**Replace:**
```html
<body class="creda">
```

### C. Composer card — remove drop overlay and file input

**Delete entirely** these lines inside `#composer-shell`:

```html
<div class="drop-overlay hidden" id="drop-overlay" aria-hidden="true">Drop not supported yet — paste text</div>
```

and

```html
<input type="file" id="file-input" class="hidden" accept="image/jpeg,image/png,image/webp,application/pdf" multiple tabindex="-1" />
```

Keep `#attachment-row` and `#parsed-links` as hidden placeholders (JS may still reference them until PACK 3).

### D. Casefile empty — honest copy

**Replace** the inner content of `.casefile-guide` with:

```html
<div class="casefile-guide glass-panel">
  <p class="casefile-empty-kicker">Case file</p>
  <p class="casefile-empty-title">What Creda shows here</p>
  <p class="casefile-empty-text">After you press Check, this pane fills with a stamped ruling, tactic tiles, evidence exhibits, and next steps — all from official sources.</p>
  <ol class="casefile-guide-steps">
    <li><strong>Stamp</strong> — HIGH RISK / NOT ENOUGH PROOF / NO CONFLICT</li>
    <li><strong>Why this is a scam</strong> — up to 6 tactic tiles with source chips</li>
    <li><strong>Exhibits</strong> — flat evidence cards (facts on the face)</li>
    <li><strong>Orders</strong> — what to do next</li>
  </ol>
  <p class="casefile-empty-hint">Paste a recruiter message on the left, then press Check.</p>
</div>
```

(No mention of screenshots, PDFs, or image upload.)

### E. Wait SVG — add `#scene-careers` and update scene list

Inside `#stage-svg`, **after** `#scene-evidence` and **before** `#scene-ocr`, insert:

```html
<g id="scene-careers" class="stage-scene is-off" aria-hidden="true">
  <!-- Lucide-style building + magnifier (hand-port, 320×100 canvas) -->
  <rect x="118" y="38" width="52" height="44" rx="4" fill="#fff" stroke="var(--ink, #0f2433)" stroke-width="1.5"/>
  <rect x="128" y="48" width="10" height="10" rx="1" fill="#e8efe8" stroke="#3d5a45" stroke-width="1"/>
  <rect x="150" y="48" width="10" height="10" rx="1" fill="#e8efe8" stroke="#3d5a45" stroke-width="1"/>
  <rect x="128" y="64" width="10" height="10" rx="1" fill="#e8efe8" stroke="#3d5a45" stroke-width="1"/>
  <rect x="150" y="64" width="10" height="10" rx="1" fill="#e8efe8" stroke="#3d5a45" stroke-width="1"/>
  <circle cx="200" cy="52" r="14" fill="#eff4ff" stroke="#155eef" stroke-width="1.5"/>
  <line x1="210" y1="62" x2="222" y2="74" stroke="#155eef" stroke-width="2" stroke-linecap="round"/>
  <circle cx="196" cy="48" r="6" fill="none" stroke="#155eef" stroke-width="1.5"/>
</g>
```

**Delete** the entire `#scene-ocr` group (OCR not live without VLM):

```html
<g id="scene-ocr" class="stage-scene is-off">
  ...
</g>
```

**Optional polish:** Remove the literal `QWEN` text from `#scene-qwen` — replace with a scale/balance icon path only (PACK 4 will refine vectors).

### F. Result board — move `#judgment-host`

**Current structure (wrong):**
```html
<div class="result-board">
  ...
  <div id="exhibits-host" class="board-exhibits"></div>
  ...
  <div class="followup-composer" ...>...</div>
</div>
<div id="judgment-host" class="hidden" aria-hidden="true"></div>
```

**Target structure:**
```html
<div class="result-board">
  <div class="result-toolbar">...</div>
  <div id="ruling-host" class="board-stamp-host"></div>
  <h2 id="board-headline" class="board-headline"></h2>
  <p id="board-meta" class="board-meta"></p>
  <div id="orders-host" class="board-actions"></div>
  <div id="tactics-host" class="board-tactics"></div>
  <div id="exhibits-host" class="board-exhibits"></div>
  <div id="judgment-host" class="hidden" aria-hidden="true"></div>
  <p id="board-consequence" class="board-consequence visually-hidden" aria-live="polite"></p>
  <div id="conversation-host" class="board-thread"></div>
  <div class="followup-composer glass-panel" id="followup-composer">...</div>
</div>
```

`#research-host` and `#result-error` stay **siblings** of `.result-board` inside `#view-result` (unchanged).

---

## Verify (hard-fail)

```bash
cd /Users/siva/Documents/first_commit_hack/frontend
grep -c 'creda-baseten\|creda-v58\|creda-v62' index.html   # must be 0
grep -c 'class="creda"' index.html                          # must be 1
grep -c 'drop-overlay\|file-input\|scene-ocr' index.html    # must be 0
grep -c 'scene-careers' index.html                          # must be 1
grep 'creda-build' index.html                               # must show v65-ui-rewrite
grep -A2 'exhibits-host' index.html | grep judgment-host    # judgment-host follows exhibits-host inside result-board
```

Open `index.html` in browser (or serve locally): DOM inspector shows `#judgment-host` as child of `.result-board`.

---

## Next pack

→ [UI_PACK_2_css_rewrite.md](./UI_PACK_2_css_rewrite.md)
