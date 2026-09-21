# Creda Live MVP Architecture Diagram — Notes

**PNG:** `docs/CREDA_LIVE_MVP_ARCHITECTURE.png` (also `/workspace/creda-arch.png` on the agent box)  
**Size:** 3600×2200 px  
**Generated:** 2026-09-19 (IST) with Python + Pillow  
**Region:** `ap-south-1` (Mumbai)

## What the diagram shows

Left-to-right swimlanes for the **live** WorkOffer Shield MVP path:

| Lane | Components |
|------|------------|
| **CLIENTS** | Amplify UI, Telegram `@CredashieldBot`, Browser upload |
| **EDGE** | API Gateway HTTP API `x1ed4uf5q9` |
| **INTAKE** | Intake Lambda → DynamoDB Cases + S3 Evidence |
| **EVIDENCE** | WorkerQueue (SQS) → Gatherer+Searcher Lambda → Forum index |
| **JUDGE** | QwenQueue (SQS) → ECS Fargate `creda-qwen-cpu` (warm=1) → llama.cpp Qwen3-4B |
| **SCHEDULE** | EventBridge `CredaDailyIngest` → `evidence-refresh` Lambda → Forum index |

## Primary request path

1. Client hits API Gateway (`/cases`, `/health`, `/upload-url`, `/reports`, `/telegram`).
2. Intake Lambda creates the case (DynamoDB), stores evidence objects (S3), enqueues **WorkerQueue**.
3. Gatherer+Searcher consumes the queue, resolves employer / ATS / tactics, attaches forum exhibits, enqueues **QwenQueue**.
4. ECS Fargate task (`creda-qwen-cpu`, desired/warm = 1) polls QwenQueue and runs **llama.cpp** with **Qwen3-4B**.
5. Verdict / status writes back to **DynamoDB Cases** (bottom highway on the diagram).

## Scheduled path

- EventBridge rule **CredaDailyIngest** (`cron(0 6 * * ? *)` in SAM) invokes **evidence-refresh** (`creda-mumbai-evidence-refresh`), which refreshes forum / ATS stamps used as exhibits.

## Explicit non-goals (footer)

This Live MVP diagram intentionally **excludes**:

- SageMaker
- g4dn / GPU inference hosts
- Cognito

Inference is **CPU Fargate + llama.cpp Qwen3-4B only**.

## Regeneration

```bash
python3 -m venv /tmp/creda-arch-venv
/tmp/creda-arch-venv/bin/pip install Pillow
/tmp/creda-arch-venv/bin/python docs/render_creda_live_mvp_architecture.py
# outputs:
#   docs/CREDA_LIVE_MVP_ARCHITECTURE.png
#   /workspace/creda-arch.png  (when run on the agent box)
```

On the Mac checkout, copy the PNG to:

`/Users/siva/Documents/first_commit_hack/docs/CREDA_LIVE_MVP_ARCHITECTURE.png`

## Source of truth

Aligned with `docs/CREDA_MVP_ARCHITECTURE_INVENTORY.md` and `docs/MVP-HARDENED-ARCHITECTURE.md` (live API id, queues, ECS service name, daily ingest schedule).


## Lock (2026-09-19)
**NO multimodal live.** Text-only judge path. Screenshot/PDF/VLM = not ready until g4dn/vLLM ships.
