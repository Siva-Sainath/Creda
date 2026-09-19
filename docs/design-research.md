# Creda layout design research

**Captured:** 2026-09-19 via live browser + CDP (`Emulation.setDeviceMetricsOverride`, `Runtime.evaluate` computed styles).  
**Not from memory.** Brand assets, copy, logos, and exact brand colours are **not** for reuse. Layout structure, spacing rhythm, grid behaviour, and interaction patterns only.

**Screenshot root:** `docs/screenshots/research/`

---

## 1. ElevenLabs (`https://elevenlabs.io/`)

### Pages inspected
| Page | URL | Screenshot(s) |
|------|-----|----------------|
| Home | `/` | `elevenlabs-home-1920.png`, `1440`, `1024`, `768`, `390` |
| Creative | `/creative` | `elevenlabs-creative-1440.png` |
| Agents | `/agents` | `elevenlabs-agents-1440.png` |
| Text-to-speech | `/text-to-speech` | `elevenlabs-tts-1440.png` |
| Pricing | `/pricing` | `elevenlabs-pricing-1440.png` |
| Enterprise | `/enterprise` | `elevenlabs-enterprise-1440.png` |
| Blog | `/blog` | `elevenlabs-blog-1440.png` |
| Docs | docs landing | `elevenlabs-docs-1440.png` |

### Viewport behaviour (home)
| Width | What fills the screen | What is constrained |
|------:|----------------------|---------------------|
| 1920 | Full-bleed cream canvas; nav edge-to-edge | Inner content ~1144–1280px band |
| 1440 | Same; side margins ~148px each if inner ~1144 | Hero + feature band inside container |
| 1024 | Near full width; gutters shrink | 12-col grids still active |
| 768 / 390 | Single column; stacked hero | No horizontal scroll observed |

### Live DOM / CSS (home @ 1440, measured)
- **Body:** `bg rgb(253,252,252)`; font `Inter`; `18px` / `28.8px` on body at some breakpoints; overflow-x hidden.
- **Fonts:** Body Inter; display `Waldenburg`. H1 @ 1440: `48px` / `52px`, letter-spacing `-0.96px`. (At narrower probes H1 was also ~48px with `tw-max-w-lg` until `lg`.)
- **Header:** Fixed top bar, height token `--header-height: 4rem`. Full viewport width; logo left, links center/left cluster, Log in + pill Sign up right.
- **Main:** `max-width: none`, width = viewport. Full-bleed sections; **inner** containers take the max-width.
- **Primary content max-width (observed class):** `tw-max-w-[30rem] md:tw-max-w-[51.75rem] xl:tw-max-w-[71.5rem]` → computed **1144px** at 1440.
- **Footer:** `tw-container`, width **944px** at 1024 with `margin: 64px 40px 0`, padding-bottom `128px` (`--section-py-xl: 10rem` scale).
- **Hero layout:** Two-column feel — large H1 left (~564px wide), supporting copy + CTAs beside/below. Not a single centered card.
- **Feature stage:** Large cream panel `rgb(245,243,241)`, `border-radius: 24px`, internal grid with `gap` **48–64px**, product tabs as rounded-full / ~14–9999px radius pills.
- **12-column grid:** `lg:tw-grid-cols-12` with `gap-x` **48px** (`lg:tw-gap-x-12`).
- **Full-bleed vs contained:** Sections are edge-to-edge; readable text sits in container. Negative-margin “bleed” utilities (`--full-bleed`) push panel edges slightly past the text column.
- **Breakpoints (from CSS media rules):** `25rem`, `40rem` (640), `48rem` (768), `53rem`, `64rem` (1024), `80rem` (1280), `96rem` (1536). Also `prefers-reduced-motion`, `hover: hover`.
- **Spacing tokens (root):** `--spacing-outer-content: 5–6.25rem` (varies by probe), `--spacing-container-gutter: 0.625rem`, `--section-py-xl: 10rem`.
- **Sticky/fixed:** Fixed header `z-[9998]`; sticky side fade rails on carousels.
- **Motion:** Soft opacity/transform on load; tabs and carousels. Respects reduced-motion media query presence.
- **Surfaces:** Light only on marketing home. Soft panels, little hard border; depth via surface colour shift more than heavy shadow.
- **Long text:** Body ~18px; paragraphs stay inside max-width bands (~45–72ch effective). Headlines use `text-balance`.

### Pattern summary (ElevenLabs)
1. Page shell is full viewport; **max-width only on content bands**, not on `main`/`body`.
2. Large section vertical rhythm (multi-rem py).
3. Soft rounded “stage” panels for interactive product demos.
4. Fixed slim nav; primary CTA as solid pill.
5. 12-col grid + large column gaps for desktop composition.

---

## 2. Baseten (`https://www.baseten.co/`)

### Pages inspected
| Page | URL | Screenshot(s) |
|------|-----|----------------|
| Home | `/` | `baseten-home-1920.png`, `1440`, `1024`, `768`, `390` |
| Pricing | `/pricing` | `baseten-pricing-1440.png` |
| Model library | `/library` (product) | `baseten-library-1440.png` |
| Model page | GLM-5.3 product | `baseten-model-glm53-1440.png` |
| Docs | docs | `baseten-docs-1440.png` |
| Blog | blog | `baseten-blog-1440.png` |
| Customers | `/customers` | `baseten-customers-1440.png` |

### Viewport behaviour (home)
| Width | What fills the screen | What is constrained |
|------:|----------------------|---------------------|
| 1920 / 1440 | Full-bleed white canvas + dashed blueprint grid | Inner `container max-w-[1296px]` |
| 1024 | Container nearly full; logo grids compress | Nav wraps/compacts |
| 768 / 390 | Stacked hero; logo grid collapses | No horizontal scroll observed |

### Live DOM / CSS (home @ 1440, measured)
- **Viewport:** 1440×900; `docW == innerW` (no overflow-x).
- **Body:** Transparent over white main; system UI sans stack.
- **Main:** `bg-b-fills-100` → `rgb(255,255,255)`, width **1440**, height tall (~7561), **max-width none**.
- **Container:** `.container.w-full.max-w-[1296px].px-4` → **1296px** wide, `padding: 24px 16px`, `margin: 0 72px` (centering gutters ~72px each at 1440).
- **Nav:** `flex … col-span-12 h-[38px]`, width **1264** inside container. Full-bleed header band; items in container.
- **H1:** `NeueAlteGrotesk`, **88px** / **80px**, letter-spacing **-1.76px**, width ~620. Left-aligned in wide column — hero uses width for logos/grid below, not for stretching the sentence.
- **Hero section:** `w-full`, `md:h-[500px]`, overflow hidden — true full-bleed band.
- **Logo / trust grid:** Multi-column cells aligned to dashed background grid — **uses horizontal space for structure**, not empty gutters.
- **Breakpoints (observed):** 576, 640, 768, 992, 1024, 1150, 1280, 1400, 1536; plus small max-width tweaks; `prefers-reduced-motion`.
- **Borders / cards:** Hairline / dashed grid lines define cells more than drop shadows. Buttons: outlined “LOG IN”, solid dark “GET STARTED”.
- **Accent:** Mint green used sparingly (announcement banner) — **do not copy colour**; copy the “sparse accent strip” idea only.
- **Docs / blog:** More contained reading columns; docs use sidebar + content (two-pane workspace pattern relevant to Creda).

### Pattern summary (Baseten)
1. **App-like full-bleed shell** with a **~1296px** content max inside fluid gutters.
2. **Structural grid** (lines / columns) to make wide layouts feel intentional.
3. Massive display type + short measure for body under it.
4. Two-pane patterns on docs (nav rail + main).
5. Dense but aligned logo/feature matrices instead of one narrow card.

---

## 3. Creda live (`https://main.d32sg54oqu2gcb.amplifyapp.com/`)

### Build
- Meta `creda-build`: **`baseten-20260919-58-single-card`**
- Body classes: `creda-baseten creda-v58` (+ `view-wide` when session restored)

### Screenshots
| Viewport | File |
|----------|------|
| 1920 | `creda-live-1920.png` |
| 1440 | `creda-live-1440.png` |
| 1024 | `creda-live-1024.png` |
| Result @ 1440 | `creda-live-result-1440.png` |

### Live DOM / CSS (@ 1440, measured)
| Node | Width | Left | max-width | Notes |
|------|------:|-----:|-----------|-------|
| `body` | 1440 | 0 | none | `--bg #f3f1ec`, Plus Jakarta Sans |
| `.shell` | **720** | **360** | **720px** | `margin: 0 360px` — **360px dead gutter each side** |
| `main` | 720 | 360 | 1392px (token, unused) | Nested inside shell |
| `.topbar` | 720 | 360 | 1392px | Same column |

**Root tokens still declare** `--col: min(1360px, calc(100vw - 3rem))` and `--col-wide: min(1400px, …)` but **v58 overrides `.shell` to 720px**, so the wide tokens never win for the page chrome.

### Problem (observed)
At 1440, **half the viewport is empty mesh background**. Intake, wait, and ruling all stack in the same 720px column. This matches a marketing widget, not an ElevenLabs/Baseten product shell.

### What still works (features)
Intake composer + chips + Telegram row; wait / prestream; result stamp + exhibits + follow-up; report sheet. Layout is the failure mode, not feature loss.

---

## 4. Patterns to adopt (structure only)

| Pattern | From | How Creda should use it |
|---------|------|-------------------------|
| Full-bleed page shell; max-width on content bands only | Both | Root `100dvh/100vw`; kill `.shell { max-width: 720px }` |
| Inner container ~1200–1300px with fluid side gutters (`clamp` / `px-4` + auto margins) | Baseten 1296; ElevenLabs ~1144–xl | Workspace max ~min(1280–1400px, 100vw − gutter) |
| Two-pane / split workspace on desktop | Baseten docs; EL 12-col hero | ≥1024: left intake, right case file |
| Text measure ≤ ~60–70ch; panels unrestricted | Both | Cap paragraphs/headlines, not panes |
| Fixed/slim top bar full width | Both | Keep Creda topbar edge-to-edge |
| Soft stage panel for interactive primary surface | ElevenLabs cream stage | Composer / case file as large panels, not tiny cards |
| Structural grid / alignment to justify width | Baseten dashed grid | Subtle pane split + column gap, not copied mint/grid art |
| Sticky primary action / follow-up | EL sticky rails; product apps | Pin follow-up to bottom of **right pane** |
| Section rhythm via CSS variables | EL `--section-py-*`, gutters | Creda spacing scale tokens |
| Collapse to single column ≤1023 | Both | Intake then results; sticky Check |
| Reduced-motion respect | Both | Keep existing GSAP reduced path |

### Explicitly do **not** adopt
- ElevenLabs Waldenburg / Inter stack (Creda keeps Plus Jakarta + JetBrains Mono).
- Baseten mint accent or dashed blueprint background art.
- Any logos, hero illustrations, or marketing copy.
- Purple/glow aesthetic (Creda mesh palette stays).

### Target shell (recommendation for Step 3)
```
┌─ topbar (full width) ─────────────────────────────────────┐
│ Creda …                                          health   │
├─ workspace (min 100dvh - header, fluid gutters) ──────────┤
│ ┌──────── left pane ─────┐ ┌──── right pane ────────────┐ │
│ │ intake / composer      │ │ empty | wait | ruling      │ │
│ │ chips, safety          │ │ stamp hero + sections      │ │
│ │                        │ │ follow-up sticky bottom    │ │
│ └────────────────────────┘ └────────────────────────────┘ │
├─ telegram band (full width slim) ─────────────────────────┤
└─ footer slim ─────────────────────────────────────────────┘
```
Tablet/mobile: stack left→right as single column; no horizontal scroll.
