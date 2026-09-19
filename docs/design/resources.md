# Creda WorkOffer Shield — resource ledger (Gate 0)

Hosting: **AWS Amplify Hosting** — static SPA (`frontend/index.html` → `dist/index.html`), API injected at build via `amplify.yml`.

| Resource | Use | Screens | Amplify fit |
|---|---|---|---|
| 21st.dev Input Bar (serafimcloud) | Glass composer, attach, send | Intake | Vanilla port, no extra bundle |
| 21st.dev Safari (ruixen.ui) | Mock browser chrome + tabs | Wait stream | CSS only |
| ui.rechesoares flip-card | Exhibit front/back provenance | Result exhibits | CSS 3D transform, no lib |
| ui-layouts liquid-glass | Gradient border glass panels | Composer, ruling, panels | `backdrop-filter`, GPU ok |
| Vercel AI SDK Branch | Agent stream timeline nodes | Wait stream | DOM only |
| reactbits split-text | Hero word blur stagger | Intake hero | GSAP already loaded |
| animata bento-grid | 6-col varied exhibit spans | Result exhibits | CSS grid |
| lukacho mock-browser | Tab bar on wait browser | Wait | HTML/CSS |
| neobrutalism chart | Confidence bar on ruling | Result ruling | CSS bar, no chart lib |
| GSAP 3 | Page load, exhibits, stream pulse | All views | ~45KB, single script tag |
| CredaShieldArt | Inline SVG hero + scan | Intake | No WebGL (removed Three.js) |
| cult-ui / kokonutui / lightswind | Not ported yet | — | Would need React; skipped for vanilla SPA |
| tweakcn | Creda tokens in `:root` | Global | Custom palette, not tweakcn export |
| uiverse / unicorn.studio | Not used | — | Decorative; violates restraint principle |

Framework: vanilla HTML/CSS/JS single file. Node: build-time sed only. Rendering: 100% static + client fetch to Mumbai API.

Performance budget (targets): initial HTML+inline CSS+GSAP < 200KB gzipped equivalent; no WebGL; poll-based async for judge.
