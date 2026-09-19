# Wake-up status — Creda demo (2026-09-19)

**You can close the lid.** `caffeinate` is running (PID check: `pgrep -fl caffeinate`).

## Ready for judge demo?

| Layer | Status |
|-------|--------|
| Backend API + SageMaker judge | **Ready** — E2E all passed (~28s) |
| Live UI (Amplify job **28**) | **Ready** — Three.js pipeline + full-bleed split deployed |
| Telegram bot | **Blocked** — needs bot token from you ([setup](TELEGRAM_SETUP.md)) |
| Custom domain | **Not configured** — needs your domain + DNS |

**Demo link:** https://main.d32sg54oqu2gcb.amplifyapp.com/

Hard-refresh (Cmd+Shift+R) after opening to bypass CDN cache.

## What was completed while lid was closed

1. **CredaPipeline3D** — WebGL node graph + particles on landing (`#hero-canvas`) and wait view (`#wait-canvas`); stage rail drives active node; respects `prefers-reduced-motion`
2. **Full-bleed intake** — `view-bleed` body class; composer left, pipeline right on desktop
3. **Removed dead SVG** — old `flow-a/b/c` intake animation references cleaned up
4. **Amplify deploy** — job 28 **SUCCEED**
5. **E2E** — `scripts/test_e2e_full.sh` — **ALL PASSED**
6. **Docs** — `TELEGRAM_SETUP.md`, this file

## Quick demo script (2 min)

1. Open the Amplify URL → health dot should go green
2. Click **Amazon fee scam** demo chip → **Check this offer**
3. Watch wait view: Three.js pipeline + live stream + exhibits
4. Ruling: **high_risk** with fee/UPI exhibits
5. Optional: **Stripe clean** demo → `unverified` / vacancy match

## Still on you

- **Telegram:** follow `docs/TELEGRAM_SETUP.md` after creating a @BotFather token
- **Custom domain:** Amplify console → Domain management → add CNAME at your registrar
- **Gmail extension:** code stub exists in `extension/`; not wired for judge demo

## Ops commands

```bash
# Re-deploy UI only
cd frontend && API="https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com"
sed "s|__CREDA_API_URL__|$API|g" index.html > dist/index.html
# then amplify create-deployment / upload / start-deployment (see scripts/deploy_all.sh)

# E2E sanity
./scripts/test_e2e_full.sh

# AWS login if expired
aws login --profile creda-dev
```

## API

`https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com` — `judgeMode: creda`, multimodal upload enabled.
