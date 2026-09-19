# Creda WorkOffer Shield

Verify job offers against official employer sources before you reply. Creda combines deterministic checks, curated evidence bundles, and a Qwen-based judge to produce a stamped verdict, exhibits, and next steps.

**Live demo**

| Surface | URL |
|---------|-----|
| Web UI | https://main.d32sg54oqu2gcb.amplifyapp.com |
| API | https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com |

Region: `ap-south-1` (Mumbai). AWS profile for operators: `creda-dev`.

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Deployment](#deployment)
- [GPU judge (optional)](#gpu-judge-optional)
- [Testing](#testing)
- [Configuration](#configuration)
- [Documentation](#documentation)
- [License](#license)

## Overview

Creda is built for competition and demo use: a single-page intake UI, an async case API, and a worker that assembles evidence from ATS listings, domain signals, scam tactic indexes, and optional multimodal input (screenshots and PDFs). The model returns structured JSON (verdict, headline, reasoning, exhibits, next actions). Deterministic rules annotate the packet but do not silently override the model stamp on the product path.

## Features

- **Case intake**: paste offer text, inline URLs (auto-detected), screenshots, or PDFs
- **Evidence pipeline**: employer registry, vacancy index, channel patterns, hiring pipeline profiles, official ATS sources
- **Verdict surface**: ruling stamp, tactic tiles, exhibit slips, follow-up conversation with snapshot preservation on re-verify
- **Report scam**: submit new tactic reports from the results view
- **Telegram bot**: same checks via `@CredashieldBot` (see `docs/TELEGRAM_SETUP.md`)
- **Chrome extension**: capture page context and selected text from careers pages (`extension/`)

## Architecture

```
Browser / Telegram / Extension
            |
            v
    API Gateway (HTTP)
            |
            v
    Intake Lambda  ------>  DynamoDB (cases)
            |
            v
         SQS queue
            |
            v
    ECS judge worker  ---->  S3 (attachments, bundles)
            |                    |
            |                    +--> Curated evidence (deploy/bundle/)
            v
    Qwen judge (Fargate text and/or g4dn GPU multimodal)
```

| Component | Role |
|-----------|------|
| `backend/intake` | REST API: create case, poll status, upload URLs, health, reports |
| `backend/worker` | Legacy Lambda worker path (deterministic + optional Strands) |
| `infra/qwen-ecs` | ECS task definitions, judge worker, vLLM GPU template |
| `infra/template.yaml` | SAM stack (`creda-mumbai`) |
| `frontend/` | Static SPA hosted on Amplify |
| `deploy/bundle/` | Pre-built evidence JSON consumed at runtime |
| `scripts/` | Deploy, ETL, GPU up/down, test catalog |

Multimodal judging uses **vLLM + Qwen3-VL-4B** on **ECS EC2 g4dn.xlarge** when the GPU stack is up. Text-only fallback uses **Fargate + llama.cpp** with Qwen3-4B GGUF. SageMaker is not used on the live path.

## Repository layout

```
.
├── backend/           # Lambda handlers and shared libraries
├── data/              # Source datasets for ETL (private/ is gitignored)
├── deploy/bundle/     # Runtime evidence bundle uploaded to S3
├── docs/              # Operator guides, handoffs, architecture notes
├── extension/         # Chrome extension (unpacked load)
├── frontend/          # index.html SPA + amplify.yml
├── infra/             # SAM and ECS CloudFormation templates
├── schemas/           # JSON schemas for agent output
├── scripts/           # Deploy, test, ETL, GPU automation
├── DEPLOY.md          # Step-by-step deploy checklist
└── AWS-ARCHITECTURE.md
```

## Prerequisites

- Python 3.12+
- AWS CLI v2 with credentials for the target account
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) for infrastructure deploy
- Docker (for `sam build --use-container` and ECS image builds)
- `jq`, `curl`, `zip` for Amplify manual deploy

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Build curated bundle (if not present)
python scripts/run_etl.py
python scripts/build_deploy_bundle.py

# Local frontend (injects API URL placeholder)
bash scripts/serve_frontend.sh
```

Open the URL printed by the serve script. Set `CREDA_API_URL` to the deployed API when testing against Mumbai.

## Deployment

Full sequence (API + bundle upload):

```bash
bash scripts/deploy.sh
```

Amplify UI (from `frontend/`):

```bash
export CREDA_API_URL=https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
mkdir -p dist
sed "s|__CREDA_API_URL__|${CREDA_API_URL}|g" index.html > dist/index.html
# Then upload dist/ via Amplify console or scripts/deploy_all.sh
```

Verify health after deploy:

```bash
curl -s "${CREDA_API_URL}/health" | jq .
# Expect: ok: true, dataReady: true
```

See `DEPLOY.md` for troubleshooting, cost notes, and Strands/Bedrock options.

## GPU judge (optional)

Warm multimodal path on g4dn (approximately USD 0.579/hr in Mumbai):

```bash
bash scripts/creda_gpu_up.sh    # ASG desired=1, vLLM sidecar
bash scripts/creda_gpu_down.sh  # scale down when credits are low
bash scripts/deploy_qwen_gpu_ecs.sh
```

Details: `docs/ARCHITECT_G4DN_NOTE.md`, `docs/CREDA_CURSOR_MVP_SHIP_G4DN.md`.

## Testing

```bash
# API smoke
bash scripts/smoke_mvp.sh

# Full catalog (21 cases; warns on agent fallback by default)
bash scripts/run_test_catalog.sh
CREDA_TEST_STRICT=true bash scripts/run_test_catalog.sh

# Prompt injection fixtures
bash scripts/test_injection_fixtures.sh

# Live UI journey (Playwright)
bash scripts/test_ui_journey.sh
```

Test prompts and matrix: `docs/TEST_PROMPTS.md`, `scripts/test_cases.json`.

## Configuration

| Variable | Purpose |
|----------|---------|
| `CREDA_API_URL` | API base URL for frontend build and scripts |
| `CREDA_UI_URL` | Amplify URL for E2E tests |
| `AWS_PROFILE` | CLI profile (default `creda-dev`) |
| `JUDGE_BACKEND` | `vllm` or `llama` on ECS worker |
| `CREDA_TEST_STRICT` | Fail test catalog on agent fallback |

Frontend build tag is in `<meta name="creda-build">` inside `frontend/index.html`.

## Documentation

| Document | Contents |
|----------|----------|
| `DEPLOY.md` | Deploy checklist and failure modes |
| `AWS-ARCHITECTURE.md` | Console and stack reference |
| `docs/CREDA_CURSOR_MVP_SHIP_G4DN.md` | MVP ship brief (GPU, UI, acceptance) |
| `docs/TELEGRAM_SETUP.md` | Bot webhook and onboarding |
| `docs/TEST_PROMPTS.md` | Regression prompts |
| `extension/README.md` | Chrome extension load instructions |

## License

Proprietary. All rights reserved unless a separate license file is added by the repository owner.
