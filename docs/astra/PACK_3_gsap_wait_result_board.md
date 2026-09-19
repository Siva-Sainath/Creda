```
COMPOSER 2.5 | Phase 3: GSAP wait + visual result board

Branch: creda/mvp-g4dn-ship
Modes: /architect then /poteto-mode
No GitHub PR unless the human explicitly asks.
SageMaker: stay deleted.
Live UI: https://main.d32sg54oqu2gcb.amplifyapp.com
Live API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
Notion playbook: https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd
```

## Branch guard (run first)

```bash
cd /Users/siva/Documents/first_commit_hack
git branch --show-current    # must print creda/mvp-g4dn-ship
git status -sb
test -f frontend/motion.js && test -f frontend/app.js
```

Phase 1 (`agentStage`, `rulingSnapshot`) and Phase 2 (shell, motion.js split) must be merged before this pack.

## Goal

Server-driven wait playlist with >=700 ms dwell per stage. Visual ruling board replaces text walls. Follow-up preserves the board. Physical stamp, tactic tiles, bento exhibits, rich nextActions.

## Real file paths

| Area | Paths |
|------|-------|
| Motion | `frontend/motion.js` |
| App logic | `frontend/app.js` |
| Styles | `frontend/styles.css` |
| Markup | `frontend/index.html` |
| Stage enum source | Poll payload field `agentStage` from API |
| Presentation | `infra/qwen-ecs/presentation.py`, `judge.py` |
| Tests | `scripts/test_followup.sh`, `scripts/test_ui_journey.mjs` |

## Notion kit map for this phase

| Kit | Surface |
|-----|---------|
| GSAP 3 | All timelines, stamp slam, exhibit stagger |
| React Bits split-text | Headline reveal inside `tlVerdict` |
| Neobrutalism components | Physical stamp (thick border, hard shadow) |
| Berlix flip-card | Tactic tiles (CSS 3D flip, front/back) |
| Animata Bento grid | Exhibit bento, varied spans |
| Lukacho Mock Browser | Official checks stage showing real careers domain |
| Uiverse / CodePen | Stamp press micro-animation |
| Vercel AI Elements Branch | Follow-up thread appended under board |

## Step 1: Server-driven stage machine

In `frontend/app.js`, replace timer-based and `agentProgress` string stage mapping with:

```javascript
var STAGE_ORDER = ["intake", "signals", "official_checks", "vision", "verdict"];
var STAGE_TO_TL = {
  intake: "tlIntake",
  signals: "tlEvidence",
  official_checks: "tlSearch",
  vision: "tlVision",
  verdict: "tlVerdict"
};
```

On each poll:

- Read `data.agentStage` from API
- Advance playlist only when enum changes
- Enforce >=700 ms minimum dwell per stage (compress only if API returns READY early)
- Never jump to "Writing the ruling" at ~5 s

On READY:

- Kill active wait timeline
- Play result reveal (stamp slam once)

## Step 2: Build timelines in motion.js

| Timeline | User sees | Copy line |
|----------|-----------|-----------|
| `tlIdleExplain` | Rotating explain strip (replaces channel bar) | "Paste a Telegram DM..." |
| `tlIntake` | Offer drops into case folder | "Filing the offer into a case..." |
| `tlEvidence` | Magnifier, exhibit slips peel off | "Pulling signals: domain, fees, channels..." |
| `tlSearch` | Mock browser with real careers domain | "Checking listings and known scam patterns..." |
| `tlVision` | Page tiles scan when attachments present | "Qwen reading your pages..." |
| `tlVerdict` | Stamp press onto ruling card | "Qwen stamping the ruling..." |

Rules:

- Use GSAP timelines, not ad-hoc CSS thrash
- `gsap.matchMedia()` for `prefers-reduced-motion: reduce` jumps to end state
- Transform aliases only (`x`, `y`, `scale`, `rotation`, `opacity`)
- No WebGL, no marquee spam

## Step 3: Visual result board

Replace paragraph dumps in `frontend/app.js` render path with:

1. **Stamp** in `#ruling-host`: physical HIGH RISK / CLEAR / NEEDS REVIEW. Split fill vs text classes for contrast. GSAP stamp-slam on reveal.
2. **Headline**: one line, split-text stagger via `tlVerdict`.
3. **Tactic tiles**: 2 to 5 flip-cards from `matchedTactics[]` or `tactics[]`. Name + one-line why.
4. **Exhibit bento**: unique slips from `evidence[]` or presentation blocks. Dedupe by source URL. No repeated Amazon paragraph.
5. **Orders**: `nextActions[]` as `{label, detail, tone}`. Normalize plain strings on client if API still sends strings. Never render empty `<strong>Next step</strong><span></span>`.
6. **Why accordion**: one tap to full reasoning, not a wall by default.

## Step 4: Follow-up preserves board

On follow-up response:

- Append conversation bubble under the board (Branch pattern)
- Do not re-render stamp, headline, or nextActions from follow-up payload
- Compare `#ruling-host` text before and after (must be identical)
- If searcher ran, show small "checked listing" chip on the bubble

Confirm backend `rulingSnapshot` merge from Phase 1 is working.

## Step 5: Official checks mock browser

Replace deleted debug chrome with Lukacho-style mock browser only during `official_checks` stage:

- Show the real domain from searcher or parsed offer URL
- No `creda://` scheme anywhere in the DOM
- Hide mock browser after stage advances

## Step 6: Extend UI tests

Update `scripts/test_ui_journey.mjs`:

- Run at 1440 px and 390 px
- Assert no `creda://` in page text
- Assert `#ruling-host` text identical before and after follow-up
- Assert next-steps list non-empty
- Assert exhibit titles unique (Set size equals list length)
- Assert follow-up dock computed style includes sticky or fixed

## Do

- Drive wait stages from `agentStage` enum
- Enforce >=700 ms dwell per stage
- Build visual ruling board (stamp, tiles, bento, orders)
- Preserve ruling on follow-up
- Dedupe exhibits by source URL
- Normalize `nextActions` to rich objects
- Respect `prefers-reduced-motion`

## Do not

- Key stages off `agentStreamText` or raw JSON chunks
- Show debug `creda://agent/stream` chrome
- Clobber ruling board on follow-up
- Render repeated exhibit paragraphs
- Leave empty Next step cards
- Invent verdicts client-side
- Open a GitHub PR

## Acceptance

- [ ] Wait dwell enforced; no jump to "Writing the ruling" at ~5 s
- [ ] No debug stream chrome; no `creda://` in DOM
- [ ] Stamp readable with contrast (HIGH RISK / CLEAR / NEEDS REVIEW)
- [ ] Headline one line with split-text reveal
- [ ] Tactic tiles render as flip-cards
- [ ] Exhibit bento shows unique slips (no repeated paragraphs)
- [ ] nextActions never empty; rich label and detail
- [ ] Follow-up adds bubble; ruling board unchanged
- [ ] Searcher follow-up shows checked listing chip
- [ ] `prefers-reduced-motion` skips animation
- [ ] Notion kits hand-ported (not npm)
- [ ] `test_ui_journey.mjs` passes at 1440 px and 390 px
- [ ] No GitHub PR opened
