# Grok handoff — Creda UI layer on LLM judge backend

**Product:** Creda WorkOffer Shield  
**User:** Job seekers in India (and global) checking recruitment messages before paying or sharing documents.  
**Live UI:** `https://main.d32sg54oqu2gcb.amplifyapp.com`  
**API:** `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`

---

## What we are building

Creda is an **evidence-backed recruitment scam checker**.

1. User pastes an offer (email, SMS, WhatsApp text).
2. Backend **gathers evidence** from official employer policies, domain checks, scam tactic patterns, and vacancy indexes.
3. **Qwen3-4B judge** (CPU on ECS) reads that evidence packet and decides:
   - `high_risk` — strong scam signals
   - `unverified` — not enough to confirm either way
   - `no_conflict_found` — checked sources align with a legitimate offer
4. The same judge call returns **structured UI blocks** (not free-form HTML). The frontend renders blocks deterministically.

The LLM is the **judge and presenter**. Lambda code gathers facts; it does not override the verdict unless the model times out (rule fallback).

---

## Backend shape (what the UI consumes)

### Case lifecycle

| `status` | Meaning for UI |
|---|---|
| `QUEUED` | Show step 1 “Running evidence checks…” |
| `COMPLETED` + `verdict=pending` | Show step 3 “Agent is judging…” |
| `COMPLETED` + `agentStatus=STREAMING` | Show streaming text from `agentStreamText` |
| `COMPLETED` + `agentStatus=READY` + real verdict | Render full result |

Poll `GET /cases/{caseId}` with header `X-Case-Token` every **1.5s**, up to **120s**.

### Key JSON fields

```json
{
  "caseId": "uuid",
  "status": "COMPLETED",
  "verdict": "high_risk | unverified | no_conflict_found | pending",
  "headline": "short summary line",
  "evidence": [{ "id", "tier", "check", "outcome", "excerpt", "sourceUrl" }],
  "matchedTactics": [{ "tactic_id", "display_name", "user_guidance" }],
  "unresolved": ["still unknown..."],
  "agentStatus": "PENDING | RUNNING | STREAMING | READY",
  "agentStreamText": "partial JSON while generating",
  "agentReasoning": "2-3 sentence judge explanation",
  "agentConfidence": 0.85,
  "agentGuardrailNote": "optional safety note",
  "agentPresentation": {
    "version": 2,
    "blocks": [{ "type": "...", "props": { ... } }]
  },
  "conversationTurns": [{ "role": "user|agent", "text": "..." }]
}
```

### Follow-up

`POST /cases/{caseId}/followup` with `{ "answerText", "question" }` → re-gathers evidence → re-judges → new blocks.

---

## Design philosophy (frontend)

### Principles

1. **Trust through structure, not prose walls.** Verdict first, evidence second, actions third.
2. **Tier literacy without jargon.** Show T1/T2 pills; never let T3 alone justify “scam” labeling in copy.
3. **Agent-visible, not agent-opaque.** Show `agentReasoning` in a subdued panel so users see *why* the judge decided.
4. **Progressive disclosure.** Stream partial output during wait; do not flash a blank spinner for 90s.
5. **Performance for deployment.** Static HTML + vanilla JS on Amplify. No framework bundle. Poll, do not WebSocket (API Gateway simplicity).

### Visual system (existing tokens — extend, do not replace)

```css
--risk: #b42318     /* high_risk */
--safe: #087443     /* no_conflict_found */
--warn: #9a6700     /* unverified */
--blue: #155eef     /* primary actions */
```

Typography: Inter/system sans. Cards with 12px radius. Agent shell uses blue border gradient (`agent-shell` class).

### Information hierarchy (top → bottom)

1. **Step rail** (5 steps: Intake → Evidence → Verdict → Qwen UI → Follow-up)
2. **Verdict banner** (largest text, color by `verdict`)
3. **Agent reasoning** (1 short paragraph, collapsible on mobile)
4. **Explanation block**
5. **Safe actions** (urgent tone for “do not pay”)
6. **Evidence highlights** (grid of cards with tier + outcome pills)
7. **Scam tactic highlights**
8. **Uncertainty / still unknown**
9. **Follow-up chips** (drive reverification)
10. **Evidence timeline** (deterministic Lambda evidence, with source links)

---

## Qwen block schema (render deterministically)

The judge may only emit these `type` values. Frontend maps `type` → renderer (see `BLOCK_RENDERERS` in `frontend/index.html`).

| Block type | Purpose | Required props |
|---|---|---|
| `verdict_banner` | Hero verdict | `title`, `subtitle` |
| `explanation` | Plain-language summary | `text` |
| `research_status` | What was checked | `label`, `items[]` |
| `evidence_highlights` | Cited checks | `items[]` with `check`, `text`, `tier`, `outcome` |
| `tactic_highlights` | Scam patterns matched | `items[]` with `title`, `guidance`, `tacticId` |
| `uncertainty` | Open questions | `items[]` strings |
| `safe_actions` | Next steps | `items[]` with `label`, `detail`, `tone` (`urgent`/`primary`/`neutral`) |
| `follow_up_questions` | Chips for reverification | `items[]` strings |
| `conversation` | Follow-up thread | `turns[]` with `role`, `text` |

**Required minimum per judgment:** `verdict_banner`, `explanation`, `safe_actions`. Server backfills from fallback if missing.

### UI components Grok should prefer

These are easy for Qwen to fill reliably and cheap to render:

| Component | Why |
|---|---|
| Verdict banner + 2-sentence explanation | Small token budget, high user value |
| 2–3 safe action cards | Structured JSON, clear CTAs |
| Evidence highlight cards (max 4) | Reuses Lambda evidence ids |
| Follow-up chips (max 3) | Drives retention loop |
| Research status bullet list | Shows “we did work” during wait |

**Avoid asking Qwen for:** custom layouts, markdown tables, nested accordions, charts, or arbitrary HTML. Stick to the block registry.

---

## Recommended UI enhancements (Grok scope)

### During wait (performance + UX)

- Show **deterministic evidence timeline** as soon as `status=COMPLETED` even while `verdict=pending` (data already in response).
- Animate `agentStreamText` in a monospace “live judgment” panel (already started).
- Display elapsed timer (“Judging… 42s”) so 60–120s feels intentional.

### After judgment

- **Confidence meter** from `agentConfidence` (0–1). Hide if fallback.
- **Cited evidence chips** from `agentCitedEvidence` linking to timeline cards.
- **Guardrail footnote** when `agentGuardrailNote` set (small, not alarming).
- Mobile: collapse evidence grid to single column; sticky “Do not pay” urgent action.

### Follow-up UX

- Pre-fill textarea when user taps a follow-up chip.
- After reverification, show `conversation` block at top of agent shell.

### Do not build yet

- WebSocket streaming (poll is enough for MVP).
- Client-side LLM calls (all inference stays on ECS).
- Custom component types without backend schema change.

---

## Performance constraints

| Constraint | Implication for UI |
|---|---|
| Judge latency 30–120s CPU | Long poll window, progressive UI, show evidence early |
| Single ECS task | One case judged at a time; show queue message if needed |
| 280 max tokens judge output | Keep blocks concise; no long essays |
| Amplify static hosting | No SSR; bake `__CREDA_API_URL__` at build |
| No GPU yet | Do not promise “instant” AI |

### Amplify deploy

```bash
# From frontend/
sed 's|__CREDA_API_URL__|https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com|g' index.html > dist/index.html
# Zip dist/ → Amplify console upload or CLI
```

---

## Demo narratives (for design copy)

1. **Amazon + Gmail + fee** → red verdict, fee policy citation, “do not pay” urgent action.
2. **Stripe official careers** → green or amber, no fee conflict.
3. **Vague remote role** → unverified, follow-up chips for employer and sender.
4. **Follow-up supplies official link** → reverification, updated blocks.

---

## Files to edit

| File | Role |
|---|---|
| `frontend/index.html` | All UI + `BLOCK_RENDERERS` + poll logic |
| `frontend/amplify.yml` | Build spec |
| `infra/qwen-ecs/judge.py` | Judge rubric + block schema (backend) |
| `infra/qwen-ecs/presentation.py` | Fallback blocks + sanitization |

---

## Success criteria for Grok delivery

- [ ] User always sees **something useful within 10s** (evidence timeline while judging).
- [ ] Final screen shows **verdict + reasoning + ≥3 blocks** without layout break on mobile.
- [ ] Follow-up flow obvious (chips + textarea + reverify button).
- [ ] No new block types without updating `judge.py` and `BLOCK_RENDERERS`.
- [ ] Lighthouse: keep single HTML file; defer non-critical CSS; no heavy fonts beyond Inter.

---

## Reference: why thinking mode is off

Qwen3 hidden thinking adds hundreds of tokens before visible output. On CPU that multiplies wait time. We use **short explicit `reasoning` in JSON** instead. Grok copy should say “Creda explains its judgment” not “chain-of-thought model”.
