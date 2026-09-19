# COMPOSER — FULL VIEWPORT REMODEL (hard-fail) · no PR

`/architect` then `/poteto-mode`  
Branch: `creda/mvp-g4dn-ship` · **DO NOT open a PR**  
Repo: `/Users/siva/Documents/first_commit_hack`  
Live (broken feel): https://main.d32sg54oqu2gcb.amplifyapp.com/  

## Open these in the IDE browser / your browser BEFORE coding (mandatory)

1. https://elevenlabs.io/ — every major band + 1–2 nav pages. Note **full-bleed** sections, edge-to-edge header, content that **uses** the width (not a shy centered postcard).  
2. https://www.baseten.co/ — dashed column grid filling the frame, huge tight type, square CTAs, SVG stage, packet ribbon (editorial/technical — NOT mesh/glass orbs).  

Steal **layout geometry + rhythm**, not their logos/brand colors.

---

## HARD FAIL CONDITIONS (auto-fail the task)

If after deploy ANY of these are true, you **failed** — keep going:

- [ ] Main work column still feels like a ~700px postcard in empty cream/white void  
- [ ] You only changed `--col` / meta `creda-build` / colors without rewriting intake+results DOM  
- [ ] Separate Screenshot/PDF tombstone still exists  
- [ ] Telegram still only a collapsed `<details>`  
- [ ] Results still show pipeline/stream/debug clutter or empty Next steps  
- [ ] You opened a PR  

Live CSS already has `--col: min(1360px, …)` but the **UI still looks constrained** because of centered lede (`max-width: 36rem`), skinny composer, unused side void, and postcard composition. **Fix composition, not the CSS variable alone.**

---

## LAYOUT TARGET (Creda = tool, not marketing clone)

### Shell (ElevenLabs-like frame use + Baseten structure)
- `html, body, .shell { min-height: 100dvh; width: 100%; }`
- Topbar **edge-to-edge** (full viewport width, inner pad `clamp(1rem, 3vw, 2rem)`).
- Main workstage: `width: 100%; max-width: min(1440px, 100vw - 2rem); margin-inline: auto` AND children **stretch to that width**.
- **Kill** decorative empty gutters that make a floating card. If you keep Baseten dashed grid, it must span the workstage (columns visible across the usable width).
- Desktop ≥960: intake = **full-width composer band** OR `1.2fr` composer + `0.8fr` SVG explain stage (GSAP). Never composer + empty upload column.
- Mobile: single column; composer full bleed of the pad; no horizontal scroll.

### Intake (judge-obvious)
1. DELETE second Screenshot/PDF dashed panel.  
2. ONE composer card **width 100% of workstage** (not max-width 36rem).  
3. Drop + (+) on that card only.  
4. Fee/Kit chips max 3 under card.  
5. Telegram **always visible** row (bot link + 3 steps) — not collapsed.  
6. H1 large/tight (Baseten scale); lede may wrap but **must not** force the whole layout to 36rem.

### Wait
- GSAP `tlPreStream` ≥700ms/scene BEFORE tokens: file → signals → tools → Qwen weighing.  
- Wait canvas uses workstage width (SVG not capped at 340px postcard).

### Results (same view as Telegram `?case=` link)
Order only: Stamp → 1 headline → ≤5 tactic tiles in a **wide grid** → ≤6 unique exhibits → rich nextActions → follow-up that **does not wipe** board.  
DELETE: agentStream logs, pipeline walls, empty Next step, creda:// debug.

### Backend locks (unchanged)
Qwen warm g4dn only; no rules backup as success; Check &lt;60s warm; no SageMaker.

---

## FILES

Rewrite structure in `frontend/index.html`, `frontend/styles.css`, `frontend/app.js` (or current entry paths). Remove/override rules that set `max-width: 36rem` / `40rem` on the **layout** (lede ok shorter; **composer/ruling board must be wide**). Bump `creda-build`.

---

## ACCEPTANCE (screenshot proof required)

Desktop 1280 + mobile 390:

1. Workstage clearly uses most of the viewport width (composer/ruling ≥ ~1100px on 1280 screens).  
2. No upload tombstone; Telegram visible.  
3. Pre-stream GSAP before tokens.  
4. Results scannable, not cluttered.  
5. Side-by-side note: which ElevenLabs + Baseten layout rules you ported (bullet list in commit message).  
6. No PR.

## DONE
Amplify URL + new `creda-build` · before/after screenshots · checklist all checked.
