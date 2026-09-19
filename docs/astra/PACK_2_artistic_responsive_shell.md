```
COMPOSER 2.5 | Phase 2: Artistic responsive shell (Notion hand-ports)

Branch: creda/mvp-g4dn-ship
Modes: /architect then /poteto-mode
No GitHub PR unless the human explicitly asks.
SageMaker: stay deleted.
Live UI: https://main.d32sg54oqu2gcb.amplifyapp.com
Notion playbook: https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd
```

## Branch guard (run first)

```bash
cd /Users/siva/Documents/first_commit_hack
git branch --show-current    # must print creda/mvp-g4dn-ship
git status -sb
ls frontend/index.html frontend/styles.css frontend/app.js
```

## Goal

Full-width desktop tool surface. Mobile full-bleed composer. Creda mesh palette preserved. Delete redundant channel bar and debug stream chrome. Sticky follow-up and report panel patterns. Split GSAP motion into `frontend/motion.js`.

## Real file paths

| Area | Paths |
|------|-------|
| Markup | `frontend/index.html` |
| Styles | `frontend/styles.css` |
| Logic | `frontend/app.js` |
| Motion (new) | `frontend/motion.js` |
| Build | `frontend/amplify.yml`, `scripts/deploy_all.sh` |
| Design refs | `docs/design/resources.md`, `docs/design/design-system.md` |

## Notion kit map for this phase

| Kit | Surface | Implementation |
|-----|---------|----------------|
| Creda mesh palette | Global `:root` tokens | Keep `--bg`, `--bg-mesh-blue`, `--bg-mesh-sage`, `--bg-mesh-teal`, `--ink`, `--blue`, `--risk`, `--safe`. Do not import dark tweakcn theme. |
| 21st.dev Input Bar | Composer shell | Retarget `.composer-shell`, circular + attach |
| ui-layouts Liquid Glass | Judgment shell only | Retarget existing `.liquid-glass`, not global chrome |
| Kokonut / Cult UI / Lightswind | Sticky follow-up dock, chips, skeletons | CSS only in `styles.css` |
| coss origin | Report side panel / bottom sheet | New `#report-panel` region |
| Simple Icons / SVG Repo | Topbar and trust row icons | Inline SVG in `index.html` |

Excluded this phase: GSAP timeline wiring (Phase 3), stamp slam animation (Phase 3).

## Step 1: Layout width

In `frontend/styles.css`:

- Use `--col-wide: min(1400px, calc(100vw - 3rem))` for main tool column on desktop
- Remove the ~680 to 720 px postcard feel
- At >=960 px, case board spans full useful width with side gutters only
- At <640 px, full-bleed composer, no horizontal overflow

In `frontend/index.html`:

- Add `view-bleed` body class where appropriate
- Desktop: composer left, pipeline or stage right on intake if split layout exists

## Step 2: Delete redundant UI

Remove from `frontend/index.html` and `frontend/styles.css`:

- `.input-channels` bar (Email | Telegram | DM | Screenshot)
- `#browser-wrap` mock browser with `creda://agent/stream` URL
- Any `#hero-canvas` or Three.js script tags
- Inline report textarea footer (move to report panel)

In `frontend/app.js`:

- Remove bindings to `data.agentStreamText`
- Remove stream panel render functions tied to debug chrome

Replace idle explain strip target with a container for Phase 3 `tlIdleExplain`.

## Step 3: Sticky follow-up and report

Desktop (>=960 px):

- `#followup-composer` or `.followup-dock` with `position: sticky` at bottom of case board
- `#report-panel` as right side panel (ghost trigger in result aftercare)

Mobile (<640 px):

- Sticky bottom follow-up dock with >=44 px tap targets
- Report as bottom sheet (`#report-sheet`), not buried footer

## Step 4: Split motion.js

Create `frontend/motion.js`:

- GSAP plugin registration
- Timeline factory stubs: `tlIdleExplain`, `tlIntake`, `tlEvidence`, `tlSearch`, `tlVision`, `tlVerdict`
- `prefers-reduced-motion` guard via `gsap.matchMedia()`
- Export init called from `app.js`

Update `frontend/index.html` to load `motion.js` after GSAP CDN.

Update `frontend/amplify.yml` and `scripts/deploy_all.sh` to copy all four files into `dist/`.

## Step 5: Creda mesh palette audit

Confirm `:root` tokens in `frontend/styles.css`:

```
--bg: #f3f1ec
--bg-mesh-blue: rgba(21,94,239,.09)
--bg-mesh-sage: rgba(61,90,69,.07)
--bg-mesh-teal: rgba(45,168,154,.06)
--ink: #0f2433
--blue: #155eef
--risk: #b42318
--safe: #087443
```

Keep mesh drift animation on `body`. Verdict-tinted radial overlays on `body[data-verdict=...]` stay.

Do not replace with a dark tweakcn export. User rejected that direction.

## Step 6: Deploy preview

```bash
export CREDA_API_URL=https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
mkdir -p frontend/dist
cp frontend/index.html frontend/dist/
cp frontend/styles.css frontend/dist/
sed "s|__CREDA_API_URL__|${CREDA_API_URL}|g" frontend/app.js > frontend/dist/app.js
cp frontend/motion.js frontend/dist/
```

Verify at 1440 px and 390 px in browser devtools.

## Do

- Hand-port CSS and SVG patterns only (no npm kits)
- Keep Creda mesh palette
- Split motion into `motion.js`
- Delete channel bar and debug browser chrome
- Build sticky follow-up and report panel/sheet
- Expand to full useful width on desktop

## Do not

- Install React or npm UI libraries on Amplify
- Apply dark tweakcn theme export
- Add WebGL or Three.js
- Leave `agentStreamText` UI bindings
- Open a GitHub PR
- Rewrite as a marketing landing page

## Acceptance

- [ ] Desktop full useful width at >=960 px (no cream gutters wasting 40% of viewport)
- [ ] Mobile full-bleed composer at <640 px, >=44 px targets, no clipped labels
- [ ] `.input-channels` bar removed
- [ ] `#browser-wrap` and `creda://` chrome removed
- [ ] No `three` script in built page
- [ ] Sticky follow-up dock on desktop and mobile
- [ ] Report opens as side panel (desktop) or bottom sheet (mobile)
- [ ] Creda mesh palette preserved in `:root`
- [ ] `frontend/motion.js` exists and loads from `index.html`
- [ ] `amplify.yml` deploys all four frontend files
- [ ] Notion kits hand-ported as CSS/SVG (not npm)
- [ ] No GitHub PR opened
