# Creda Demo Readiness Plan

**Goal:** Judge-ready link with working intake → wait → ruling, polished UI, documented gaps.

## Backend ↔ Frontend connection (measured 2026-09-19)

| Surface | Status | Evidence |
|---------|--------|----------|
| `GET /health` | **Live** | `status: ok`, `judgeMode: creda`, `multimodal.uploadUrl: true` |
| `POST /cases` | **Live** | Creates case, returns `caseId` + `accessToken` |
| `GET /cases/{id}` | **Live** | Poll verdict, evidence, `agentPresentation`, stream |
| `POST /cases/{id}/followup` | **Live** | Needs `answerText` (UI fixed) |
| `POST /upload-url` | **Live** | S3 presign for JPEG/PNG/WebP/PDF |
| `GET /coverage` | **Not routed** on prod API | Returns 404 (health embeds searcher stats instead) |

**Strands/Qwen** run server-side only. The Amplify page never talks to Strands directly.

## ATS / scraper (what works now)

From live `/health` searcher block:

- **17–18 ATS sources** (Greenhouse, Lever, Ashby boards)
- **~4.8k vacancies**, **47 employers** indexed, daily refresh
- **Per-case live fetch** when employer resolves from message
- **Does not work:** LinkedIn, Indeed, Naukri, Workday scraping; `openWebPerRequest: false`

Stripe/Amazon-style cases work when employer + links parse from the pasted message.

## Three.js on Amplify

**Yes.** Vanilla `index.html` + CDN script (same as GSAP). No build step. Use WebGL only for hero/wait scenes; dispose on view change; respect `prefers-reduced-motion`.

## UI direction (your choices)

1. **Three.js pipeline** on landing (right panel) and wait view
2. **Full-bleed split** — composer left, animation + explainer right on desktop

## Telegram bot (next after web demo)

Code exists in `creda-mumbai` stack (`telegram_bot.py`, `/telegram/webhook`). **Not enabled** until you provide:

1. Bot token from [@BotFather](https://t.me/BotFather)
2. `sam deploy` with `TelegramBotToken=<token>` and `TelegramWebhookSecret=<random>`
3. Register webhook: `https://api.telegram.org/bot<TOKEN>/setWebhook?url=<API_URL>/telegram/webhook&secret_token=<SECRET>`

## Execution order

1. UI polish (Three.js + full-bleed + wait motion) → deploy Amplify
2. Run `scripts/test_e2e_full.sh` against prod API
3. Fix any UI/API mismatches found
4. Custom Amplify domain (needs Route53/Amplify console + your domain DNS)
5. Telegram (blocked on bot token from you)

## Known judge-safe caveats

- Case tokens live in `sessionStorage` (tab-only; refresh on same tab OK)
- Long polls can take 30–90s (SageMaker judge)
- Vague employer names → fewer ATS exhibits (still returns ruling)
- No Gmail extension yet (future `sourceChannel: extension`)
