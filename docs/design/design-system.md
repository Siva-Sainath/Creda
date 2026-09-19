# Creda design system (Gate 2)

## Color roles

| Role | Token | Use |
|---|---|---|
| Background | `--bg` #f3f1ec | Page |
| Surface | `--panel` #fff | Cards |
| Text | `--ink` #0f2433 | Headings, body |
| Muted | `--muted` #5f6d7a | Helper text |
| Accent | `--blue` #155eef | Primary actions |
| Risk | `--risk` #b42318 | Errors, high-risk verdict |
| Safe | `--safe` #087443 | Clean verdict |
| Warn | `--warn` #9a6700 | Unverified |

## Type

- **UI:** Plus Jakarta Sans
- **Data:** JetBrains Mono (pills, telemetry, error details)
- Scale: 12 / 14 / 16 / 20 / 28 / 40 (clamp on hero)

## Spacing

4pt base. Composer padding 1rem. Section gaps .75–1rem.

## Errors (user-facing)

Never show HTTP codes or internal error names. Every error card has:

1. Title (≤6 words)
2. Body (what happened + input preserved)
3. Primary button (smart fix)
4. Optional secondary (go back, copy details)

## Motion

GSAP for hero split-text and page load only. `prefers-reduced-motion` respected.

## What we removed (usefulness pass)

- Dev zone labels (`01 · Intake`) hidden
- Mantra strip hidden (was internal jargon)
- Raw evidence collapsed behind `<details>` by default
