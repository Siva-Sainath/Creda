# UI PACK 4 — Wait storyboard timing + vectors

**Prerequisites:** UI PACK 0–3 done.  
**Files:** `frontend/app.js` (WaitStoryboard, CredaStageMachine), `frontend/index.html` (SVG scenes), `frontend/styles.css` (stage-canvas polish).

---

## Goals

1. Each wait scene visible **≥ 1.4s** (`MIN_MS: 1400`).
2. Stamp scene appears only when `readyData` exists (not on timer alone).
3. Five **visually distinct** scenes: intake → evidence → careers → qwen → stamp.
4. Human-readable labels only (no `FILE`, `QWEN`, raw pipeline tokens in UI).
5. Lucide-idiom inline SVG (24px grid, `currentColor`, stroke 1.75).
6. `prefers-reduced-motion`: static final scene, no timeline.

---

## A. WaitStoryboard changes (`app.js`)

### Constants

```javascript
var WaitStoryboard = {
  MIN_MS: 1400,
  // ...
```

### Sequence (no OCR)

```javascript
this.sequence = ["intake", "evidence", "official_checks", "qwen_weigh", "stamp"];
```

Remove `caseHadAttachment` / `ocr` branch entirely.

### Stamp gating — replace `_playStep` final-branch logic

Current bug: timer runs full sequence in ~3.5s then shows stamp before backend ready.

**New behavior:**

```javascript
_playStep: function () {
  if (!this.running) return;
  var key = this.sequence[this.stepIndex];
  // Do not show stamp until readyData exists
  if (key === "stamp" && !this.readyData) {
    CredaStageMachine.forceScene("qwen_weigh", this.lastPollData || {});
    var self = this;
    this.stepTimer = setTimeout(function () { self._playStep(); }, 400);
    return;
  }
  CredaStageMachine.forceScene(key, this.lastPollData || {});
  var self = this;
  clearTimeout(this.stepTimer);
  this.stepTimer = setTimeout(function () {
    if (!self.running) return;
    if (self.stepIndex < self.sequence.length - 1) {
      self.stepIndex += 1;
      self._playStep();
    } else {
      self.dwellComplete = true;
      self._tryFinish();
    }
  }, this.MIN_MS);
},
```

Remove the old block that forced `qwen_weigh` → `stamp` loop when `!readyData` at end of sequence.

### `markReady` — advance to stamp when backend ready

```javascript
markReady: function (data) {
  this.readyData = data;
  // If we're still before stamp, jump stepIndex to stamp-1 and advance
  var stampIdx = this.sequence.indexOf("stamp");
  if (stampIdx >= 0 && this.stepIndex < stampIdx && this.running) {
    this.stepIndex = stampIdx;
    clearTimeout(this.stepTimer);
    this._playStep();
  }
  this._tryFinish();
},
```

### `_tryFinish` — unchanged gate

Still requires `readyData && dwellComplete`.

---

## B. CredaStageMachine scene map

```javascript
scenes: {
  intake: { id: "scene-intake", label: "Opening your case file…" },
  evidence: { id: "scene-evidence", label: "Pulling scam signals…" },
  official_checks: { id: "scene-careers", label: "Checking official careers listing…" },
  qwen_weigh: { id: "scene-qwen", label: "Weighing the evidence…" },
  stamp: { id: "scene-stamp", label: "Stamping your ruling…" }
},
sceneIds: ["scene-intake", "scene-evidence", "scene-careers", "scene-qwen", "scene-stamp"],
```

**Delete** `ocr` entry.

### `pipelineWaitCopy` — human labels only

Ensure subtitles never echo:
- `writing the explanation` (interim)
- Raw `FILE`, `QWEN`, `agentStatus` values

Map pipeline keywords to:
- `searching` / `ats` → "Searching official sources…"
- `domain` / `careers` → "Checking careers listing…"
- `judge` / `weigh` → "Weighing the evidence…"

---

## C. SVG vector spec (`index.html` `#stage-svg`)

ViewBox: `0 0 320 100`. Each `<g class="stage-scene">` toggles `.is-off` when inactive.

### Scene inventory

| ID | Visual | Title (wait-title) |
|----|--------|-------------------|
| `scene-intake` | Folder + document lines | Opening your case file… |
| `scene-evidence` | Magnifying glass + pulse ring | Pulling scam signals… |
| `scene-careers` | Building windows + magnifier | Checking official careers listing… |
| `scene-qwen` | Balance scale (no "QWEN" text) | Weighing the evidence… |
| `scene-stamp` | Stamp press + RULING rect | Stamping your ruling… |

### Lucide hand-port rules

- Stroke `currentColor` or token colors (`--blue`, `--ink`, `--sage-ink`).
- `stroke-width="1.75"` `stroke-linecap="round"` `stroke-linejoin="round"`.
- `fill="none"` on icons; fills only for subtle backgrounds (`#eff4ff`, `#e8efe8`).
- No raster images, no Lordicon CDN, no emoji.

### Replace `#scene-qwen` text node

**Remove:**
```html
<text ...>QWEN</text>
```

**Add balance scale paths** (example):
```html
<g id="scene-qwen" class="stage-scene is-off">
  <line x1="160" y1="32" x2="160" y2="58" stroke="#155eef" stroke-width="2"/>
  <line x1="132" y1="40" x2="188" y2="40" stroke="#155eef" stroke-width="2"/>
  <path d="M132 40 L124 52 L140 52 Z" fill="#eff4ff" stroke="#155eef" stroke-width="1.5"/>
  <path d="M188 40 L180 52 L196 52 Z" fill="#eff4ff" stroke="#155eef" stroke-width="1.5"/>
  <rect x="148" y="58" width="24" height="6" rx="2" fill="#155eef" opacity=".25"/>
</g>
```

### Enhance `#scene-evidence` — radar sweep

Add a subtle rotating arc group `#evidence-pulse` for GSAP (or CSS `@keyframes` in styles.css):

```css
@keyframes evidencePulse {
  0%, 100% { opacity: .4; transform: scale(.92); }
  50% { opacity: 1; transform: scale(1); }
}
.stage-scene:not(.is-off) #evidence-pulse {
  animation: evidencePulse 1.4s var(--ease) infinite;
}
```

---

## D. GSAP per-scene (in `forceScene`)

| Key | Animation |
|-----|-----------|
| `intake` | sheet slides up, folder tab bounce |
| `evidence` | glass circle `back.out`, pulse ring |
| `official_checks` | building fade in, magnifier sweep |
| `qwen_weigh` | scale arms subtle oscillation |
| `stamp` | press `scale` + `rotation` (existing) |

All use `fromTo` with `clearProps` on complete. Skip entirely when `CredaMotion.reduced`.

---

## E. Prestream rail copy

Update `.prestream-step` labels in HTML if needed:

```html
<span class="prestream-step" data-step="file">Opening</span>
<span class="prestream-step" data-step="signals">Signals</span>
<span class="prestream-step" data-step="check">Careers</span>
<span class="prestream-step" data-step="qwen">Weighing</span>
```

Rail step `stamp` maps to `qwen` visually (last step lights until stamp scene).

---

## F. Tactic tile vectors (`app.js` `tacticVectorSvg`)

Ensure ≤6 tactic icons use inline Lucide-style paths (wallet, message-circle, link, building, shield-alert). Already partially implemented ~1185 — verify each category returns SVG, not empty string.

---

## Verify (hard-fail)

**Timing:**
1. Start Check with fee-scam paste.
2. Each of 5 scenes visible ≥1.4s before next.
3. Stamp scene does **not** appear until poll returns ready verdict.
4. No scene shows "QWEN" or "FILE" as user-visible title.

**Reduced motion:**
1. DevTools → Rendering → `prefers-reduced-motion: reduce`.
2. Wait view shows static `scene-intake` or final scene without animation.
3. Result board fully opaque without GSAP.

```bash
grep 'MIN_MS: 1400' frontend/app.js
grep -c 'scene-ocr\|QWEN' frontend/index.html   # 0 for both
```

---

## Next pack

→ [UI_PACK_5_deploy_verify.md](./UI_PACK_5_deploy_verify.md)
