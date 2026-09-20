# Creda

Paste a job offer. Get a ruling before you pay.

- Live: https://main.d32sg54oqu2gcb.amplifyapp.com/
- API: `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`
- Telegram: [@CredashieldBot](https://t.me/CredashieldBot)
- Region: `ap-south-1` (Mumbai)

## Why

- Fake offers land on WhatsApp, Gmail, and LinkedIn with real company names.
- They ask for a small UPI, a "laptop deposit", or a PhonePe kit.
- We are students. We wanted a check that uses the same text, before anyone pays.

## What it does

- Paste text, a screenshot, a PDF, or a URL.
- Pulls official ATS listings, employer domain, and known fee tactics.
- Stamps one of: **high risk**, **unverified**, **no conflict found**.
- Shows exhibits and next steps.
- Same loop on the website, Telegram, and a Chrome extension.
- No login. A case token in the header is enough.

## Try these

High risk:

```
Flipkart hiring for WFH catalog tagging. Salary 35k/month. Buy starter kit Rs 2499 on PhonePe to hr.flipkart.wfh@gmail.com. Training on WhatsApp group only.
```

Unverified:

```
LinkedIn InMail from Notion Talent: We loved your profile for a remote PM role. Reply with your salary expectation. Interview tomorrow on Google Meet, no prep needed.
```

No conflict: a real Greenhouse or careers URL, no fee.

## How it is built

```
seeker -> Amplify / Telegram
       -> API Gateway (HTTP)
       -> Intake Lambda -> DynamoDB + S3
       -> SQS -> Gatherer/Searcher Lambda
       -> EventBridge (daily ATS refresh)
       -> SQS -> Fargate (Qwen 4B)
       -> poll DynamoDB -> UI
```

| Service | Role | Why this one |
| --- | --- | --- |
| Amplify Hosting | UI | Static HTTPS. No app server. |
| API Gateway HTTP API | Public routes | Cheaper than REST for this traffic. Throttle 2 req/s. |
| Lambda (ARM) | Intake, gather, ingest | Scales to zero. |
| DynamoDB on-demand | Cases, token hash, reports | Pay per request. TTL. |
| S3 | Uploads + evidence bundle | Presigned PUT. Bundle built offline, not at click time. |
| SQS | Worker queue, then judge queue | API returns 202. DLQ on failure. |
| EventBridge | Daily refresh | No always-on ETL box. |
| ECS Fargate | llama.cpp Qwen3-4B | Real stamp. Only always-on compute. |
| g4dn.xlarge (optional) | Qwen-VL for screenshots | ~USD 0.58/hour. Scale ASG to 0 after. |

No Cognito on the student path. No SageMaker on the live path.

## Cost

Request path (API Gateway + Lambda + DynamoDB + SQS + S3 + EventBridge + Amplify): free tier or a few USD/month at student volume.

| If left on | What you pay |
| --- | --- |
| Fargate judge, 4 vCPU / 8 GB, desired 1 | ~USD 5/day |
| g4dn.xlarge | ~USD 0.58/hour, only when `scripts/creda_gpu_up.sh` |
| 1,000 checks/month, Fargate off, no GPU | under USD 5 |

A weekend of judging with the text judge warm is still cheaper than one fake deposit.

## Custom domain

You cannot rename `*.amplifyapp.com`. Buy `creda.in` (or similar) in Route 53. Amplify console: Hosting, Custom domains, Add domain, Amplify-managed cert, map branch `main` to the root.

## Layout

```
backend/        Lambda
frontend/       Amplify app
infra/          SAM + ECS
deploy/bundle/  evidence JSON for S3
extension/      Chrome
scripts/        deploy, ETL, GPU, tests
schemas/        judge JSON
```

Operator steps: `DEPLOY.md`.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/serve_frontend.sh
```

```bash
export CREDA_API_URL=https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
curl -s "$CREDA_API_URL/health" | jq .
```

```bash
bash scripts/deploy.sh
bash scripts/smoke_mvp.sh
```
