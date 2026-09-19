# CURSOR — Fix “Next step” placeholders (P0) + real orders

**Modes:** `/architect` then `/poteto-mode`

Live: https://main.d32sg54oqu2gcb.amplifyapp.com/
API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
No PR unless asked. Deploy Amplify (+ backend if you change nextActions shape).

## Bug (user screenshot)
**WHAT TO DO NEXT** shows two white cards that only say **“Next step”** with empty bodies. That is broken product UX.

## Root cause (verified)
Live API returns `nextActions` as **plain strings**, e.g.:
```json
["Wait for the agent judgment", "Do not pay or share documents until the review completes"]
```

Frontend `BLOCK_RENDERERS.safe_actions` expects **objects**:
```js
item.label || item.title || item.action || "Next step"
item.detail || item.description || ""
```
When `item` is a string, `.label` is undefined → fallback **"Next step"** and blank detail.

Also interim copy “Wait for the agent judgment” must **not** remain after `status=COMPLETED` / agent READY — replace with real, verdict-specific orders.

## Fix (do all)

### 1) Frontend — normalize immediately (`frontend/index.html`)
In `synthesizeBlocks` / `safe_actions` renderer:
```js
function normalizeAction(item) {
  if (typeof item === "string") {
    return { label: item, detail: "", tone: "neutral" };
  }
  return {
    label: item.label || item.title || item.action || item.text || "Next step",
    detail: item.detail || item.description || item.guidance || "",
    tone: item.tone || item.urgency || "neutral"
  };
}
```
Never show the literal fallback “Next step” if you can use the string itself as the label.

### 2) Backend — emit rich actions (preferred)
`backend/worker/handler.py` `_next_actions` is typed to return `list[dict]`. Ensure **every** path (Lambda worker **and** ECS `qwen_worker` / `presentation.py`) writes:
```json
[{"label":"Do not pay any fee","detail":"Real employers never ask for laptop deposits or training fees.","tone":"urgent"}, ...]
```
Map from verdict + matchedTactics:
- fee/deposit → Do not pay / do not share UPI
- WhatsApp/Telegram-only → Demand official careers email / calendar invite
- free mailbox / impersonation → Open employer careers site (link if known)
- unverified → What to send Creda next (employer site, full email headers)
- Remove “Wait for the agent judgment” once judgment exists

### 3) UI craft
- Orders cards: strong label + one-line detail (not empty)
- Urgent tone for “Do not pay”
- Prefer 3–4 concrete cards, full-width in the result column

## Acceptance
1. Fee/Telegram scam → cards like “Do not pay…”, “Verify on official careers…”, **never** bare “Next step”
2. Hard-refresh Amplify shows fix
3. Paste one live case `nextActions` JSON in your reply proving shape

Hard fail: any visible card whose title is still exactly “Next step”.
