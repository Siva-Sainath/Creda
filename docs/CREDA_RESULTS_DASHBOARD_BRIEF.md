# Creda results dashboard — low-text brief (2026-09-19)

Mobbin: paid plan required (unavailable). Patterns from security-dashboard craft + prior Creda research.

## Best-of-class pattern (SOC / risk tools)

1. **One giant status** first (score / stamp / severity) — color does the talking.
2. **One short headline** (what happened) + **one consequence line** (what to do / what it means).
3. **KPI / evidence tiles in a grid** — icon + ≤1 line fact + tiny chip (source / severity). No paragraphs on tiles.
4. **Actions as chips/buttons**, not essay cards.
5. Long prose only behind a collapsed “Details” / drawer.

References: SecOps overview blocks (threat score + alert list), Shield UI (SeverityBadge + MetricCard + ThreatCard), VirusTotal-style verdict + signal grid.

## Creda locked layout (full viewport)

```
┌───────────────┬────────────────────────────────────────────┐
│ Intake        │  STAMP (legible)                           │
│ composer      │  Headline (1 line)                         │
│ chips         │  Consequence (1 line)                      │
│ Telegram      │  ┌────┐ ┌────┐ ┌────┐  ≤6 visual tiles     │
│               │  │icon│ │icon│ │icon│  smoking-gun + chip  │
│               │  └────┘ └────┘ └────┘                      │
│               │  Orders: chip row                          │
│               │  Follow-up (compact)                       │
└───────────────┴────────────────────────────────────────────┘
```

## Hard rules

- NO flip-cards. Flat tiles only; smoking-gun + source chip on the face.
- NO text walls. Max 1 sentence under stamp. Reasoning → `<details>`.
- Tactic tiles: vector icon + title ≤6 words + fact ≤12 words + source chip.
- nextActions: 2–4 short buttons (“Don’t pay”, “Verify careers”, “Report”).
- Use whole right pane; kill empty “No case open” void after Check.
- Stamp text must contrast (separate fill vs ink).
- Prefer GSAP stagger of tiles over more copy.

## Anti-patterns (current live fails)

- Flip “Why we trust this” hides the evidence judges need.
- Empty forum-intel card faces.
- Faint HIGH RISK stamp.
- Postcard 720 column / unused side gutters.
- Follow-up replacing board with “writing the explanation”.
