# Creda

## You get a job offer. Check it before you reply.

Every month, students in India get a WhatsApp hire with a company logo, a salary, and a UPI id. "Send Rs 2,500 for the kit and you are in." It is never real.

**Creda checks if a job offer is a scam.** Paste the message. Get a stamp, the sources, and what to do next. No login.

**[Open the app](https://main.d32sg54oqu2gcb.amplifyapp.com/)** · **[Telegram @CredashieldBot](https://t.me/CredashieldBot)**

![Creda path in ap-south-1: paste on Amplify or Telegram, API Gateway, gather evidence, Qwen writes the stamp](docs/architecture.png)

Live in **Mumbai (`ap-south-1`)**. That Amplify URL is the demo. It does not change.

## What you get

Three honest verdicts. We do not scare you just to scare you.

- **High risk**: money up front, fake mailbox, or known scam tactics.
- **Unverified**: a real company, but the message does not line up (vague role, no hiring path we can back).
- **No conflict found**: the company is hiring this way. Still be careful. We did not find a conflict.

Paste WhatsApp text, an email, a screenshot, or a job URL. Same check on the web and on Telegram.

## Try it

**High risk (fee + fake Amazon mail):**

```
Amazon India WFH listing specialist. Salary 42,000/month.
Pay Rs 1,999 joining kit on PhonePe to amazon.hr.wfh@gmail.com
to confirm the offer. Training only on WhatsApp.
```

**Unverified (real brand, weak process):**

```
LinkedIn InMail from Notion Talent: We loved your profile for a remote PM role.
Reply with salary. Interview tomorrow on Google Meet, no prep needed.
```

**Cleaner:** a careers-page link from a company you can name, no kit fee, no personal Gmail.

A check usually takes about a minute. The site waits on purpose. Facts run first. The model writes the stamp second.

## How it works

1. You paste the offer on the Amplify app or in Telegram.
2. **API Gateway** takes the request. **Intake Lambda** opens a case, issues a one-time token, and puts work on **SQS**.
3. **Gatherer Lambda** checks employer records, careers domains, fee/tactics, the ATS vacancy index, and forum exhibits. It does **not** scrape the open web on every paste.
4. **EventBridge** refreshes that evidence overnight, so the stamp can say unverified instead of inventing a page.
5. **Qwen on ECS Fargate** reads the evidence packet and writes the stamp, headline, confidence, cited sources, and next steps.
6. The browser polls **GET /cases/{id}**. DynamoDB holds the case. S3 holds the bundle and optional uploads.

If the model output is junk, code still has a verdict from the checks. Citations have to exist in the packet.

## What is live in Mumbai

This is the source of truth for the URL above. Not a wishlist.

| Piece | Live |
|---|---|
| UI | Amplify `https://main.d32sg54oqu2gcb.amplifyapp.com/` |
| API | API Gateway `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com` |
| Intake / gather / ingest / Telegram | Lambda (`creda-mumbai-*`) |
| Wait vs hang | SQS WorkerQueue + QwenQueue + DLQ |
| Case + token + reports | DynamoDB |
| Evidence bundle + uploads | S3 |
| Daily ATS + forum refresh | EventBridge `CredaDailyIngest` |
| Stamp | ECS Fargate `creda-qwen-cpu` (one warm task, Qwen3-4B) |
| Auth | Per-case token. No Cognito. |
| Bedrock | Off |
| SageMaker | Tried, then deleted. Not on this URL. |
| GPU g4dn | Built in repo. Not on this URL (quota). |

**Health check:**

```bash
curl -s https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com/health | jq .
```

Expect `status: ok`, `dataReady: true`, `bedrockEnabled: false`, `judgeMode: creda`, `vacancyRefresh: daily`.

## Cost (why it is this shape)

Students use it free. The bill has to stay boring.

| What | About |
|---|---|
| Text checks at hackathon volume | a few dollars |
| Keep the Qwen task warm 24/7 | ~USD 5/day |
| SageMaker GPU endpoint | killed. sticky idle cost |
| g4dn always-on | ~USD 0.58/hour if quota ever lands. not live |

One fake "joining kit" costs a student more than a month of Creda.

## Run it

**Use the live app (this is the demo):**

https://main.d32sg54oqu2gcb.amplifyapp.com/

**Telegram:** message [@CredashieldBot](https://t.me/CredashieldBot), paste an offer.

**Frontend locally (still talks to Mumbai):**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/serve_frontend.sh
```

Operator notes: `DEPLOY.md`, `docs/TELEGRAM_SETUP.md`.

## Repo

The product is **Python** (Lambda intake/gatherer/ingest, ECS Qwen worker, SAM) plus a small Amplify UI.

GitHub's language bar can look like "mostly HTML." That is saved employer policy pages under `data/raw` and `data/manual_snapshots` (evidence snapshots, not the app). There is one real UI file: `frontend/index.html`. `.gitattributes` marks those snapshots as vendored so Linguist does not treat crawl HTML as the stack.

```
backend/     Python Lambdas: intake, gatherer, ingest
frontend/     Amplify UI (one HTML file + CSS/JS)
infra/        SAM + ECS Qwen worker (Python)
scripts/      deploy and smoke tests (shell)
data/         employer snapshots, tactics, ATS sources
extension/    Chrome helper (optional)
docs/         architecture still and setup notes
```

## How it was built

Written with **Kiro** and **Cursor Agent**. Humans designed the gather-then-judge path, the Mumbai deploy, and the cost cap. The agents implemented and iterated the code.

## First Commit tracks

**Build it:** SAM CLI, Docker + DynamoDB Local, Strands in the worker, Qwen served next to the ECS worker. Agents: Kiro, Cursor Agent.

**Ship it:** Amplify, API Gateway, Lambda, SQS, DynamoDB, S3, ECS Fargate, EventBridge, CloudWatch, IAM.

Issues: [github.com/Siva-Sainath/Creda/issues](https://github.com/Siva-Sainath/Creda/issues)
