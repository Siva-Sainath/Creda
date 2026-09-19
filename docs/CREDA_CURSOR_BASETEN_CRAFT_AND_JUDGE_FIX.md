# COMPOSER — Real Baseten craft (inspected) + Qwen-only warm judge · no rules fallback

**Modes:** `/architect` then `/poteto-mode`  
**Branch:** `creda/mvp-g4dn-ship` · **no PR**  
**Repo:** `/Users/siva/Documents/first_commit_hack`  
**Live:** https://main.d32sg54oqu2gcb.amplifyapp.com/  
**Craft reference (inspected 2026-09-19):** https://www.baseten.co/  
**Notion kits:** https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd (hand-port)

---

## CRITICAL CORRECTION

Baseten is **NOT** gradient-mesh / liquid-glass / soft orb marketing.

Inspected homepage craft:
- **White canvas**, dashed vertical/horizontal column rules (`repeating-linear-gradient`, reveal via GSAP/`--revealed`)
- **No** orbs, mesh blobs, backdrop-blur cards, drop shadows, rounded SaaS cards
- Display type huge + tight (H1 ~88/80, weight 600, tracking ~−0.02em); **mono uppercase** for eyebrows/CTAs
- **Square CTAs** (radius 0, h=48); sticky **solid white** nav + dashed bottom (no blur)
- Accent = flat neon green as ink/banner/**highlighter bar behind a phrase** (not just text color)
- Hero = **one inline isometric SVG** (~hundreds of paths) + GSAP moving cubes/dots on dotted connectors + live SVG `<text>` counters — not Lottie/video
- **Packet ribbon**: stacked dashed rails, colored blocks sliding at different speeds
- Soft mint wash **only** behind diagrams; rest plain white

**Creda must steal TECHNIQUE, not the green brand or logo.** Use Creda ink/blue/risk palette with the same *editorial/technical* system.

Delete or fully replace the failed `body.creda-baseten` “strip glass / dashed form” half-pass. Ship a **visible rewrite** or the task fails.

---

## LOCKS

| Lock | Value |
|------|--------|
| Judge | **Qwen only** on warm **g4dn.xlarge + vLLM**. **No rules-engine backup** as a successful verdict path. |
| If Qwen down | Honest “Judge warming / retry” — never regex-only final stamp on Check |
| Latency | Case → ruling **&lt;60s** p95 warm (target ≤45s) |
| Capacity | ASG desired=1 for hackathon window |
| SageMaker | Stay deleted |
| UI | Vanilla + GSAP CDN; Baseten *editorial* craft above; Notion hand-ports |
| Pre-stream | GSAP explain playlist **before** tokens |
| PR | Do not open |

---

## PART 1 — Frontend rewrite (must be obviously different)

### 1A. Page system (Baseten transfer — implement all)
1. Full-bleed **dashed column grid** (divs + `repeating-linear-gradient`); GSAP draw-in of rules on load/scroll  
2. Tight display grotesk for H1/H2; **JetBrains/Chivo-style mono** uppercase for eyebrows, nav, buttons  
3. Square primary/secondary CTAs (radius 0, ~48px), 236ms custom ease, chevron nudge on hover  
4. Sticky solid nav + dashed bottom — **no** backdrop-blur  
5. Mono eyebrow chip (1px border, no radius) e.g. `CASE INTAKE`  
6. Phrase **highlighter bar** (absolute span behind key words in lede), animate scaleX from left  
7. Intake / wait **isometric or case-file inline SVG** scene; GSAP on `x/y/rotation/opacity` only (`will-change: transform`)  
8. Optional live counter labels on the diagram (tween numbers: checks run, signals found)  
9. **Packet ribbon** under hero or during wait: 4–6 dashed rails, small rects looping `xPercent` at staggered speeds (one off-color)  
10. Soft wash only behind the SVG stage; page elsewhere clean paper/white (Creda paper tint OK if still editorial)  
11. Width: use the frame (`min(1360px, 100vw - 3rem)`), not a shy postcard — gutters are grid, not empty cream void  
12. Mobile: same system scaled; sticky Check/follow-up; report sheet; ≥44px; no clip  

**Hard fail:** another meta `creda-build` bump with the same sparse form. **Hard fail:** reintroducing blob mesh / heavy glass everywhere / soft rounded SaaS cards as the “Baseten” take.

### 1B. PRE-STREAM GSAP (before tokens)
On Check → wait view immediately → play `tlPreStream` **before** first token/SSE:

| Scene | Motion | Caption |
|-------|--------|---------|
| intake | Packet/offer into folder on the SVG stage | Filing your offer into a case… |
| signals | Magnifier + fee/link markers | Pulling signals: domains, fees, channels… |
| tools | Ribbon / rail pulse | Checking listings & known patterns… |
| vision | Scan tiles if attachments | Qwen reading your pages… |
| think | Soft pulse on model mark | Qwen weighing the evidence… |

Each dwell ≥700ms (compress if early return, still ≥2 scenes). Then stream chrome or stamp. Copy says **Qwen**, never “rules”. `prefers-reduced-motion` → static captions. Hard fail: jump to tokens with no playlist.

### 1C. Result board
Physical stamp (fill ≠ text); tactic tiles; unique exhibits; rich nextActions; follow-up **must not clobber** board. Telegram quiet ≤3-step. Kill Email\|Telegram\|DM\|Screenshot bar if present.

### 1D. Notion
Hand-port tokens/bento/shimmer/mock-browser/SVG icons **into** this editorial system (don’t paste random glass marketing).

---

## PART 2 — Backend: warm Qwen only · sub-minute

- g4dn + vLLM Qwen3-VL-4B warm (desired=1); short JSON; ≤2 images; temp 0  
- **No product success via `agentSource=fallback`** — STRICT catalog fails on fallback  
- Annotators may feed packet; they do **not** replace Qwen stamp on Check  
- Fee-scam + gmail-mismatch → Qwen high_risk narrative with signals in packet  
- Fix catalog script jq `and: command not found`  
- Smoke: one Check **&lt;60s** with Qwen source  

---

## ACCEPTANCE

- [ ] Side-by-side: page reads editorial/technical like Baseten structure (dashed grid, big type, square CTAs, SVG stage, ribbon) — obviously not old form  
- [ ] Pre-stream playlist visible before tokens  
- [ ] Check → Qwen ruling &lt;60s warm; no rules-only verdict  
- [ ] STRICT catalog: no fallback passes; mismatch/fee coherent  
- [ ] Mobile sticky follow-up; ruling preserved  
- [ ] No PR  

## DONE
Architect note citing inspected Baseten techniques · Amplify `creda-build` bump · &lt;60s smoke · STRICT summary · desktop+mobile screenshots
