# CURSOR — Wait-loop animations for slow ECS (don’t let users get bored)

**Modes (mandatory):** `/architect` then `/poteto-mode`

Live: https://main.d32sg54oqu2gcb.amplifyapp.com/  
API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com  
Edit `frontend/index.html` (vanilla + **GSAP** OK; optional lightweight CSS 3D — **no** Three.js/WebGL unicorn unless already in page).  
Deploy Amplify. No PR unless asked.

## Why
ECS/llama judgment is often slower than SageMaker GPU. Today the wait UI feels like: status “queued”, tiny signal bars, static chips (LIVE / QUEUED / AGENT), and a flat step rail (INTAKE → EVIDENCE → VERDICT → JUDGMENT → FOLLOW-UP). Users get bored and bounce.

**Goal:** a continuous, purposeful wait story that explains *what Creda is doing* and *how long this stage usually takes*, even when the API is quiet for 15–60s+.

---

## /architect (write first)
1. Scene list + min dwell times  
2. How elapsed timer + “typical ECS” copy work  
3. What happens if API returns in 2s vs 45s (compress vs loop idle beat)  
4. `prefers-reduced-motion` plan  

Then `/poteto-mode`.

---

## Hard fail if any true after deploy
1. Wait view is still static labels + signal bars with no obvious motion.  
2. Stages jump Instantly to result with no visible intermediate scenes.  
3. No elapsed time / no “usually takes ~Xs on this path” hint.  
4. Decorative-only motion that doesn’t map to Intake / Evidence / OCR / Stream / Judgment.  
5. WebGL / heavy 3D that tanks mobile (keep CSS/SVG/GSAP).

---

## Build: wait storyboard (required)

### Layout (use the screen)
- Wait view should be **wide**: min-height ~70vh, centered stage ≥ min(920px, 92vw).  
- Kill the cramped 720px feel on wait.  
- Big stage SVG/CSS panel + stage rail + live copy + elapsed.

### Scenes (play even when ECS is slow)
| # | Scene | Look (animation) | Copy example |
|---|--------|------------------|--------------|
| 1 | Intake | Message sheet **slides into** case folder; tab pulses once | “Filing your offer into a case…” |
| 2 | Evidence | Exhibit slips **stagger in**; magnifier **drifts** yoyo; checks pop | “Checking domains, fees, and known scam patterns…” |
| 3 | ATS / vacancy | Mini board cards shuffle / one locks green or dashed | “Comparing to official job boards…” |
| 4 | OCR (only if attachment) | Scan-line loops over doc thumbnail | “Reading your PDF / screenshot…” |
| 5 | Judgment (ECS) | Mock browser / agent stream with **shimmer on new tokens**; if no tokens yet, **idle thinking pulse** (soft 3D card tilt via CSS `rotateY` / perspective — subtle) | “ECS judge writing the ruling…” |
| 6 | Stamp | One press (scale + 1.5° tilt) then result | “Stamping the verdict…” |

**Timing rules**
- Min dwell **≥700ms** per scene that plays.  
- If API still not READY after scene playlist: enter **ECS hold loop** on Judgment scene — breathing glow, rotating soft orb/shield (CSS 3D or SVG), cycling micro-tips every ~4s (“Still on ECS… fee patterns take a few seconds”, “Waiting for llama.cpp tokens…”).  
- Show **elapsed** `mm:ss` always.  
- Show honest band: `Typical on ECS · 15–45s` (tune from real polls if you measure; don’t fake SageMaker times).  
- When READY: finish current scene quickly → stamp → result (don’t restart playlist).  
- Fast API (<3s): **compressed** playlist still shows ≥3 beats so humans see motion.

### Replace today’s weak chrome
- Remove or demote the tiny 5-bar signal widget as the hero.  
- Stage rail: only one active; progress line fills; completed steps get a check draw.  
- LIVE / QUEUED / AGENT chips → one clear status pill driven by `agentStatus` (`QUEUED` / `RUNNING` / `STREAMING` / `READY`).  
- Primary headline must never stay stuck on “queued” while later stages are visually active — sync copy to active scene.

### Light “3D” without WebGL
Allowed and preferred:
- CSS `perspective` + `transform: rotateY()` on a judgment card (8–12°, slow yoyo)  
- Layered SVG depth (shadow blob under shield)  
- GSAP stagger / scrub-free timelines  
Forbidden for this pass: Three.js, splines, particle WebGL, looping split-text heroes.

### Reduce motion
`prefers-reduced-motion: reduce` → static finals per scene, no loops, keep elapsed + copy.

---

## Keep working
- Polling / create case / follow-up unchanged.  
- Don’t block result on animation if READY — cancel hold loop and stamp.  
- Stamp text must stay readable (no `.stampInkPress` opacity:1 solid fill over same-color text).

---

## Done checklist
1. `/architect` scene + timing summary  
2. List of motions added  
3. Screenshot: mid-wait Judgment/ECS hold with elapsed visible  
4. Screenshot: stamp → result after slow wait  
5. Amplify hard-refresh note  
6. “Ready for Grok Bot test loop”

If wait is still boring after 10s of silence, the task failed.
