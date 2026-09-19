# Creda UI skills (installed locally)

Skills pulled for the GSAP + frontend craft pass on `frontend/index.html`.

| Skill | Status | Location |
|-------|--------|----------|
| GSAP | Installed | `~/.cursor/skills/_vendor/.agents/skills/gsap-*` (via `npx skills add greensock/gsap-skills`) |
| UI UX Pro Max | Installed | `~/.cursor/skills/_vendor/.agents/skills/ui-ux-pro-max` |
| Anthropic frontend-design | Installed | `~/.cursor/skills/_vendor/.agents/skills/frontend-design` |
| Expo | Installed | `~/.cursor/skills/_vendor/.agents/skills/` (expo skills bundle) |
| skills.sh taste / oh-my-frontend | Failed | Auth required on skills.sh |

## Usage in this repo

Amplify ships **vanilla HTML/CSS/JS** only. Patterns from shadcn, dashboard, and taste skills are hand-ported as CSS. Motion uses **GSAP 3.12.7** from jsDelivr CDN and the `CredaMotion` controller in `frontend/index.html`.

## Motion map

- **Page load** — topbar, mantra, intake zone stagger
- **View transitions** — intake → wait → result fade/slide
- **Wait** — mock browser scale-in, stage rail pulse on stage change, exhibit slips slide in, stream panel pulse on new tokens
- **Result** — ruling stamp slam, glass panels stagger, exhibit bento cascade, urgent order nudge
- **Reduced motion** — `prefers-reduced-motion` disables GSAP; CSS signal rack remains as fallback
