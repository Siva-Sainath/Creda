# Creda

Check a job offer before you pay.

**Try it:** https://main.d32sg54oqu2gcb.amplifyapp.com/  
**Bot:** [@CredashieldBot](https://t.me/CredashieldBot)  
**API:** `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com` (Mumbai)

## What we built

- Paste offer text, a screenshot, or a URL. No account.
- Creda pulls official careers data and known fee tactics, then stamps **high risk**, **unverified**, or **no conflict found**.
- Same flow on the website, Telegram, and a Chrome extension.

We built this because fake Flipkart / TCS / Infosys offers keep landing on student WhatsApp with a small UPI or "laptop deposit".

## Paste these

**Scam (full demo):**

```
Flipkart hiring for WFH catalog tagging. Salary 35k/month. Buy starter kit Rs 2499 on PhonePe to hr.flipkart.wfh@gmail.com. Training on WhatsApp group only.
```

**Not enough proof:**

```
LinkedIn InMail from Notion Talent: We loved your profile for a remote PM role. Reply with your salary expectation. Interview tomorrow on Google Meet, no prep needed.
```

**Looks fine:** a real Greenhouse or careers link, no upfront fee.

## Stack (ap-south-1)

| Piece | Service |
| --- | --- |
| UI | Amplify Hosting |
| API | API Gateway HTTP API |
| Intake | Lambda, DynamoDB, S3 |
| Evidence | SQS, Lambda, EventBridge (daily refresh) |
| Judge | ECS Fargate, llama.cpp Qwen3-4B |
| Screenshots (optional) | g4dn + Qwen-VL, scaled to 0 when idle |

No Cognito on the student path. Evidence bundle is built offline and uploaded to S3 so Lambda does not run ETL on each click.

## Cost

- API path at student volume: free tier or a few USD/month.
- Warm Fargate judge (demo): about USD 5/day if you leave it on. We scale down after judging.
- GPU: about USD 0.58/hour in Mumbai, only when needed.

## Repo

```
backend/        Lambda handlers
frontend/       Static app (Amplify)
infra/          SAM + ECS templates
deploy/bundle/    Evidence JSON for S3
extension/      Chrome helper
scripts/        Deploy and tests
schemas/        Judge output JSON
docs/           Telegram setup, test prompts, architecture notes
```

Deploy: `DEPLOY.md`. Telegram: `docs/TELEGRAM_SETUP.md`.

## Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bash scripts/serve_frontend.sh
```

```bash
curl -s https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com/health | jq .
```

## Custom domain

You cannot rename `*.amplifyapp.com`. Buy a domain in Route 53, then Amplify console, Hosting, Custom domains, map `main` to the root.
