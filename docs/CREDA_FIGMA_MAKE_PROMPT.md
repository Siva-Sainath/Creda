# Creda — Figma Make Prompt (paste all of Part B into Figma Make)

**Product:** Creda WorkOffer Shield  
**Goal:** Design a competition-grade **single-screen tool UI** (not a marketing site). Export frames we can hand-port into vanilla `frontend/index.html` on Amplify.  
**Audience:** Job seekers in India checking recruitment messages before they pay fees or share IDs (WeMakeDevs judges).

---

## Part A — How to use this in Figma Make

1. New Make session → paste **Part B** in full.
2. Ask Make for **mobile (390×844)** and **desktop (1280×800)** of each frame.
3. Request **Auto Layout**, named layers, and a **Variables** collection for tokens.
4. Export: PNG/PDF for review + Dev Mode specs / SVG icons. We will rebuild in HTML/CSS (no React).
5. Reject any output that looks like a SaaS landing page, feature grid, or chatGPT clone.

---

## Part B — Prompt for Figma Make

You are a senior product designer. Design **Creda WorkOffer Shield**, a calm, artistic **case-file tool** — not a marketing website, not a dashboard, not a generic AI chat.

### Product one-liner
User pastes a recruitment email/SMS/WhatsApp message (and optionally drops a screenshot). Creda runs live backend checks + a Qwen judge and returns a **ruling** with **exhibits** so they know whether to reply, pay, or share documents.

### Mantra (tiny chrome only — never a hero headline)
- “Good design speaks first.”
- “Frontend sells the backend.”

### Absolute do / don’t

**DO**
- One primary product surface with clear states: Idle intake → Waiting → Result
- Natural-language input only for the offer text
- Easy multimodal: **circular + button** + **drag-and-drop** dropzone for screenshots/images/PDFs
- Ruling stamp + 2–4 exhibit cards + orders + follow-up chips
- Craft that “gels” like Baseten: shared spacing rhythm, construction/grid discipline, purposeful motion cues (show as prototype annotations), mono micro-labels for state
- Warm paper case-file aesthetic (trust under stress)

**DON’T**
- Marketing hero (“A calmer second opinion…”, feature grids, logos wall, pricing)
- Nested “Add details” forms (no separate sender / employer / links fields)
- Charts, neon WebGL, looping split-text animations
- Fake “API unavailable” chrome
- Chat sidebar / infinite thread as the main product
- Soft generic Tailwind SaaS card soup with no hierarchy
- Saying “Verified authentic offer”

---

### Design tokens (create Figma Variables)

| Token | Value | Use |
|-------|--------|-----|
| ink | `#0F2433` | Primary text |
| muted | `#5F6D7A` | Secondary text |
| bg | `#F3F1EC` | Page / warm paper |
| panel | `#FFFFFF` | Surfaces |
| line | `#D7E0E8` | Borders / dashed rules |
| blue | `#155EEF` | Rare accent / links |
| risk | `#B42318` | High risk |
| safe | `#087443` | No conflict found |
| warn | `#9A6700` | Unverified |
| sage | `#E8EFE8` | Soft supporting fill (wait zone) |
| radius | `12px` intake composer; `8px` cards (tighter than soft SaaS) |
| font UI | Plus Jakarta Sans (or Inter) | Body / H1 |
| font mono | JetBrains Mono | RISK / SAFE / WARN / T1 / E1 stamps |

Background: warm paper + very subtle construction grid (light dashed 24–32px) OR soft radial glow — keep it quiet. Optional low-opacity ambient orbs.

Motion notes (annotate on frames, don’t over-animate in Make):
- Exhibit cards stagger in 60–100ms apart
- Ruling stamp “lands” once
- Wait stream = live signal bars / shimmer (system alive), never blank spinner
- Urgent order: one pulse then still
- `prefers-reduced-motion` = instant

Reference craft (feel, don’t clone): baseten.co — blueprint cohesion, flat panels, mono telemetry, accent reserved for state. Keep Creda’s paper/ink identity.

---

### Information architecture

#### Frame 1 — Intake (idle)
**Layout**
- Top bar: Creda shield mark + wordmark · tiny live health pill (“API ready”)
- Centered H1: **Check a job offer before you reply.**
- One short lede (1 line): what Creda does — no manifesto

**Composer (the star — think Grok / modern AI composer, not a web form)**
- Large rounded surface with soft border
- **Single multiline natural-language field** covering most of the card  
  Placeholder: `Paste the recruiter message, or describe what they asked you to do…`
- **No “Add details” section.** No sender email / employer / links inputs. Everything lives in the message.
- Bottom toolbar inside composer:
  - Left: circular **+** button → attach screenshot / image / PDF
  - Attachments appear as removable chips/thumbnails above the toolbar
  - Large **drag-and-drop overlay** when dragging files: dashed border, “Drop screenshot or offer PDF”
  - Right: primary CTA **Check this offer** (filled ink or blue)
- Helper microcopy under composer: `Don’t paste OTPs, bank details, or passwords.`
- Optional row of **3 demo chips** below (secondary, pill): Amazon fee scam · Stripe clean · Vague ProtonMail — labeled as demos

**Empty-state art (optional, ≤1 illustration)**
- Quiet SVG scene: case file + shield + magnifier — not stock handshake

#### Frame 2 — Waiting (case running)
- Same shell; composer collapses or becomes a slim “Case opened” strip with truncated offer
- **Stage rail:** Intake → Evidence → Verdict → Judgment → Follow-up (current step emphasized)
- Elapsed timer `0:42`
- **Mock-browser chrome** panel: traffic lights + URL `creda://case/{id}` + streaming judgment text area with shimmer / signal bars
- **Live exhibit slips** appearing one-by-one as evidence arrives (2–3 placeholders shown mid-flight)
- Telemetry mono pills: `LIVE` · `EVIDENCE` · `AGENT`
- Never a lone spinner

#### Frame 3 — Result · High risk (fee scam)
- **Ruling stamp** (rotated slightly): `HIGH RISK` + headline + one consequence: “Do not pay or share documents until this is cleared through official channels.”
- Micro-metrics mono: `CONF · 0.86` · `EXHIBITS · 3`
- Collapsible “Creda explains its judgment” (2–3 sentences)
- **Exhibit bento (2–4 cards)** numbered `E1`–`E4`:
  - They said
  - We checked
  - Result (conflict / clear / unknown)
  - Tier `T1` or `T2` + optional source
- Matched scam tactics (if any) as compact list
- **Orders:** 2–3 next actions; top one urgent (sticky hint on mobile)
- **Need from you:** ≤3 follow-up chips + optional reply field
- Accordion: Full evidence dock
- Secondary: Check another · Report this scam

#### Frame 4 — Result · Unverified
Same shell; stamp `NOT ENOUGH PROOF` / warn color; emphasize follow-up chips and gaps (“Still unknown”).

#### Frame 5 — Result · No conflict found
Stamp `NO CONFLICT FOUND` / safe color; consequence honest: what aligned + limits — **never** “verified authentic.”

#### Frame 6 — Mobile variants
Intake + Wait + High-risk result at 390 width. Sticky urgent order on high risk. Thumb-friendly + and CTA.

#### Frame 7 — Component set (for Dev Mode)
- Buttons: primary / secondary / ghost / chip / demo chip
- Health pill
- Stage step
- Exhibit card (default / hover showing provenance)
- Stamp (risk / safe / warn)
- Attachment chip + drag overlay
- Signal-rack / shimmer block
- Accordion row

---

### Content samples (use real copy in mockups)

**High-risk offer (E1 narrative)**  
They said: pay INR 1200 training fee + send Aadhaar on WhatsApp.  
We checked: Amazon official careers never request fees or Aadhaar via WhatsApp.  
Result: conflict · Tier T2

**Orders**  
1. Do not pay any fee  
2. Do not share Aadhaar / PAN / bank details  
3. Verify only via official careers site

---

### Deliverables checklist for Make

Output these named frames:
1. `Creda / Desktop / Intake`
2. `Creda / Desktop / Waiting`
3. `Creda / Desktop / Result — High risk`
4. `Creda / Desktop / Result — Unverified`
5. `Creda / Desktop / Result — No conflict`
6. `Creda / Mobile / Intake`
7. `Creda / Mobile / Waiting`
8. `Creda / Mobile / Result — High risk`
9. `Creda / Components`

Also:
- Variables collection `Creda/Tokens`
- Auto Layout everywhere
- Exportable SVG icons: shield, plus, check, alert, mail, link, chevron, paperclip
- Short design note page: spacing rhythm (8px base), motion list, a11y (contrast, focus rings)

### Success criteria
A WeMakeDevs judge understands the tool in 5 seconds. Intake feels as easy as attaching a photo in a modern AI chat (+ and drop). Results feel like a case ruling with exhibits — artistic and cohesive, never a form farm or marketing landing.

Start by designing **Desktop Intake** with the composer (+ / drag-drop / natural language only), then Waiting, then High-risk Result.
