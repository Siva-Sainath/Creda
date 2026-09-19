# UI PACK 3 — app.js P0 fixes + dead code removal

**Prerequisites:** UI PACK 0–2 done.  
**File:** `frontend/app.js`  
**Keep:** API wiring, `renderResult`, polling, report sheet, GSAP CDN usage.

---

## P0-1 — Follow-up grace window (`followupReplyComplete`)

**Problem:** Line ~759 ends with `return false` — polls until 120s if agent is ready but only interim text exists.

**Add** module state near top (after `followupBaseline`):

```javascript
var followupGraceStartedAt = 0;
var FOLLOWUP_GRACE_MS = 8000;
```

**Replace** `followupReplyComplete` with:

```javascript
function followupReplyComplete(data) {
  if (!conversationPending) return true;
  var agent = normalize(data.agentStatus);
  if (agent === "running" || agent === "streaming") {
    followupGraceStartedAt = 0;
    return false;
  }
  var answer = extractFollowupAnswer(data);
  if (answer) {
    followupGraceStartedAt = 0;
    return true;
  }
  if (isInterimText(data.headline) || isInterimText(data.explanation) || isInterimText(data.agentReasoning)) {
    if (!followupGraceStartedAt) followupGraceStartedAt = Date.now();
    if (Date.now() - followupGraceStartedAt < FOLLOWUP_GRACE_MS) return false;
    return true; // grace expired — caller shows honest deferral
  }
  if (!followupGraceStartedAt) followupGraceStartedAt = Date.now();
  if (Date.now() - followupGraceStartedAt < FOLLOWUP_GRACE_MS) return false;
  return true;
}
```

In `sendFollowup` / poll completion path: when grace expires with no answer, push assistant turn:

```javascript
"Couldn't verify that yet — the ruling above still stands."
```

Reset `followupGraceStartedAt = 0` when follow-up starts and when it completes.

---

## P0-2 — Board protection during follow-up (`mergeFollowupSnapshot`)

**Problem:** When `protect` is false, `renderResult` overwrites stamp/headline/tiles.

**Replace** `mergeFollowupSnapshot` body:

```javascript
function mergeFollowupSnapshot(data) {
  if (!followupPollMode || !followupBaseline) return data;
  var merged = Object.assign({}, data);
  merged.verdict = followupBaseline.verdict || merged.verdict;
  if (followupBaseline.headline && (!merged.headline || INTERIM_REPLY_RE.test(String(merged.headline)))) {
    merged.headline = followupBaseline.headline;
  }
  if (followupBaseline.explanation) {
    merged.explanation = followupBaseline.explanation;
    merged.agentReasoning = followupBaseline.explanation;
  }
  if (followupBaseline.presentation) merged.agentPresentation = followupBaseline.presentation;
  if (followupBaseline.evidence && followupBaseline.evidence.length) merged.evidence = followupBaseline.evidence;
  if (followupBaseline.tactics && followupBaseline.tactics.length) merged.tactics = followupBaseline.tactics;
  if (followupBaseline.nextActions && followupBaseline.nextActions.length) {
    if (!extractRawActions(merged).length) merged.nextActions = followupBaseline.nextActions;
  }
  merged.conversationTurns = data.conversationTurns || merged.conversationTurns;
  return merged;
}
```

Remove the `protect` flag and early `if (!protect) return merged`.

In follow-up poll handler: call `renderResult(data, { skipReveal: true, followupOnly: true })` and when `opts.followupOnly`, **only** update `#conversation-host` (do not rewrite `#ruling-host`, `#tactics-host`, etc.).

Add to `renderResult`:

```javascript
if (opts.followupOnly) {
  $("conversation-host").innerHTML = renderConversationHtml(data);
  return;
}
```

---

## P0-3 — GSAP ghosting: replace all `gsap.from(`

| Location | Fix |
|----------|-----|
| `pageLoad` ~207–210 | `fromTo` with `{ autoAlpha: 1, y: 0 }` end + `onComplete: () => gsap.set(target, { clearProps: "opacity,transform" })` |
| `enterView` wait branch ~265–268 | Same pattern for `.prestream-rail .prestream-step`, `.stage-canvas` |
| `slipIn` ~285 | `fromTo` each node to `{ autoAlpha: 1, y: 0 }` + clearProps |

Ensure `resultReveal` still calls `forceRevealVisible` before and `onComplete` after.

---

## P0-4 — Intake busy during follow-up (`showView`)

**Find** (~876–877):
```javascript
if (name === "wait") setIntakeBusy(true);
else setIntakeBusy(false);
```

**Replace:**
```javascript
if (name === "wait") setIntakeBusy(true);
else if (!conversationPending) setIntakeBusy(false);
```

---

## P0-5 — Remove attachment / OCR path (VLM not live)

**Delete or gut:**
- `pendingAttachments`, `MAX_ATTACHMENTS`, `caseHadAttachment` usage in storyboard
- `uploadPendingAttachments` (~1119)
- `addAttachmentFiles` (~960)
- `renderAttachmentChips` (~988)
- `#file-input` / `#btn-attach` listeners in `wireComposer`
- `demo-chip` listeners (~2505)
- `CredaStageMachine.scenes.ocr` and `scene-ocr` from `sceneIds`
- `WaitStoryboard` sequence: remove `if (caseHadAttachment) this.sequence.push("ocr")`

**Update** `official_checks` scene mapping:
```javascript
official_checks: { id: "scene-careers", label: "Checking official careers listing…" },
```

**Update** `sceneIds`:
```javascript
sceneIds: ["scene-intake", "scene-evidence", "scene-careers", "scene-qwen", "scene-stamp"],
```

**Update** `forceScene` GSAP branch: animate `#scene-careers` instead of reusing `#scene-evidence` for `official_checks`.

**Update** `updatePrestreamRail` `sceneToStep`: `official_checks: "check"`.

**Update** `syncSendButton`: disable Check only on `offerText.length >= 12` (remove attachment/link shortcuts until multimodal returns).

---

## P0-6 — Delete dead functions (never called)

Remove entire function bodies and any references:

| Function | ~Line |
|----------|-------|
| `formatStreamBranches` | 354 |
| `wireInputChannels` | 1213 |
| `isWaiting` | 1288 |
| `renderStageRail` | 1340 |
| `extractStream` | 1356 |
| `renderWaitPipeline` | 1410 |
| `updateWaitTelemetry` | 1438 |
| `renderOfficialChecks` | 1512 |
| `renderChipRows` | 1825 |
| `toggleLinksPanel` | 1877 |
| `blocksByType` | 1887 |
| `renderEvidenceDock` | 1896 |
| `CredaMotion.streamPulse` | 277 |

**Simplify** `CredaShieldArt` to no-op (or delete calls in `showView`) — `#intake-steps` does not exist.

**Remove** `CredaMotion.startHintCycle`, `setHint`, `startSignalRack` if they only target `#hint-cycle` / `.signal-rail`.

**Fix** `renderStreamError` — stop writing to `#stream-body`; use `#result-error` or `#intake-error` only.

---

## P0-7 — Orphan DOM references to remove

Search `app.js` for these ids/classes and delete or guard with null checks:

```
hint-cycle, intake-steps, signal-rack, demo-chip, btn-attach, channel-chip,
stage-rail, stream-body, wait-pipeline, tl-status, tl-agent, browser-url,
official-checklist, need-chips-host, ask-chips-host, need-section, ask-section,
links-panel, link-input-1, link-input-2, evidence-dock, evidence-dock-summary,
drop-overlay, file-input, scene-ocr
```

---

## Verify (hard-fail)

```bash
cd /Users/siva/Documents/first_commit_hack/frontend
grep -c 'gsap\.from(' app.js                    # must be 0
grep -c 'demo-chip\|btn-attach\|file-input\|scene-ocr\|stream-body' app.js  # must be 0
grep -c 'wireInputChannels\|renderStageRail\|renderWaitPipeline' app.js     # must be 0
grep -c 'scene-careers' app.js                  # must be >= 1
node --check app.js                             # syntax OK
```

**Manual:**
1. Run Check → result at opacity 1.
2. Follow-up with domain question → answer or 8s deferral; stamp unchanged.
3. Check another ×3 → no ghost tiles.
4. Console: zero errors.

---

## Next pack

→ [UI_PACK_4_wait_vectors.md](./UI_PACK_4_wait_vectors.md)
