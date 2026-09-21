# Creda WorkOffer Shield — CURRENT MVP Architecture Inventory

**Inventory date:** 2026-09-19 (Asia/Calcutta)  
**Scope:** What exists and works **today** on live Mumbai (`ap-south-1`). No aspirational future.  
**Sources:** GitHub branch `creda/mvp-g4dn-ship` (cloned to box), live API curls, Amplify `app.js`, repo SAM/ECS templates + ops docs.  
**AWS CLI:** Profile `creda-dev` was **not configured on this executor box** — CloudFormation/EventBridge/ECS list calls could not run. Live API + code + `docs/ARCHITECT_G4DN_NOTE.md` (same-day) used instead. Re-run CLI checks from a machine with `aws login --profile creda-dev` to confirm ASG desired counts.

| Live surface | Value |
|---|---|
| UI | https://main.d32sg54oqu2gcb.amplifyapp.com/ (Amplify app `d32sg54oqu2gcb`, branch `main`) |
| API | https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com |
| Account (from docs) | `966499105769` · region **`ap-south-1`** · profile **`creda-dev`** |
| Lambda stack | `creda-mumbai` (deployed from **external** path `…/Codex/…/creda-aws-backend/outputs/creda-backend`, not from this repo’s thin `backend/intake/app.py`) |
| Judge | ECS Fargate cluster/service **`creda-qwen-cpu`** · `JUDGE_BACKEND=llama` · llama.cpp Qwen3-4B GGUF |
| GPU g4dn / vLLM | **Code + templates present; NOT deployed as of 2026-09-19 architect note** |
| SageMaker judge | **Deleted / stay deleted** |
| Cognito | **NO** (per-case `X-Case-Token` HMAC hash) |
| Step Functions | **NO** (not in live path) |
| SNS | **NO** on critical path |

Live `/health` (probed 2026-09-19):

```json
{
  "status": "ok",
  "dataReady": true,
  "bedrockEnabled": false,
  "judgeMode": "creda",
  "agentQueueConfigured": true,
  "searcher": {
    "atsSources": 17,
    "employersIndexed": 47,
    "vacancyRefresh": "daily",
    "openWebPerRequest": false,
    "forumIngestion": true,
    "lastForumIngest": 1789805038,
    "lastAtsRefresh": 1789805038,
    "bundleVersion": "creda-demo-2026-09-17"
  },
  "intakeChannels": ["web", "extension", "telegram"],
  "multimodal": { "uploadUrl": true, "ocr": true }
}
```

`lastForumIngest` / `lastAtsRefresh` ≈ **2026-09-19 13:33 IST** (08:03 UTC).

---

## Feature matrix (YES / NO / PARTIAL)

| Capability | Status | Evidence |
|---|---|---|
| **EventBridge** | **YES** (daily schedule ingest) | SAM `Schedule` → `CredaDailyIngest` in `infra/template.yaml`; health `forumIngestion: true` + fresh timestamps; live cases attach `ev_forum_*` exhibits. Exact rule names/targets not re-listed via AWS CLI on this box. |
| **Searcher (ATS / vacancy)** | **YES — wired + used on Check** | Live pipelineLog: “Searching official ATS…”. Stripe case: live ATS call failed → **667 cached vacancies**; link format checked. Amazon: “No ATS connector… does not browse arbitrary websites”. `openWebPerRequest: false`. No `ev_search_*` IDs observed on these cases. |
| **Telegram** | **PARTIAL** | UI deep-links `@CredashieldBot`; `/health` lists `telegram`; `POST /telegram/webhook` returns **401** without secret (route live). Docs: needs BotFather token + webhook secret; groups unsupported. |
| **Multimodal (upload + OCR)** | **PARTIAL / YES API** | `POST /upload-url` returns S3 presigned PUT to `creda-mumbai-evidencebucket-*`; health `uploadUrl`+`ocr` true. UI accepts JPG/PNG/WebP/PDF. GPU VL path **not** live — text Fargate judge is production. |
| **Follow-ups** | **YES (API) / PARTIAL (UX)** | `POST /cases/{id}/followup` → 202, stage `reverifying`, restarts gather+judge. Live: READY again ~100s. Issues: ruling headline resets; conversationTurns often **user-only** (no assistant bubble); no `rulingSnapshot` freeze. |
| **Injection defense** | **PARTIAL** | `infra/qwen-ecs/injection_guard.py` pattern scrub; judge guardrails in docs/tests. Not fully proven here beyond code presence. |
| **Reporting** | **YES** | `POST /reports/scam` → 202 `reportId`, `PENDING_REVIEW`. UI report sheet wired. Optional EventBridge `creda.scam.reported` not confirmed live. |
| **Streaming** | **PARTIAL (poll stream)** | **No SSE**. UI polls `GET /cases/{id}` every 1.5s; `agentStatus` RUNNING→STREAMING→READY; `agentStreamText` fills during STREAMING. |
| **Bedrock / Strands headline** | **NO on live** | `bedrockEnabled: false`. |
| **g4dn + vLLM Qwen3-VL** | **NO (not deployed)** | Templates/scripts exist (`infra/qwen-ecs/template-gpu.yaml`, `creda_gpu_up.sh`). Architect note: GPU ECS not deployed; Fargate desired=1 is judge. |
| **Extension channel** | **PARTIAL** | Listed in health; `extension/` stub; not demo-critical. |

---

## 1. Frontend → API routes (`frontend/app.js` + live Amplify)

`API_URL` on Amplify is baked to the Mumbai execute-api host (not `__CREDA_API_URL__` placeholder).

| UI action | Method + path | Notes |
|---|---|---|
| Health dot | `GET /health` | Expects `dataReady` / ok |
| Create case | `POST /cases` | Body: `offerText`, `locale`, optional `links`, `attachments` / `screenshotKey`, `sourceChannel: web` |
| Poll / “stream” | `GET /cases/{caseId}` + header `X-Case-Token` | Poll 1.5s, max ~120s; uses `agentStreamText`, `agentStatus`, evidence |
| Follow-up | `POST /cases/{caseId}/followup` | Body: `answerText` / `text` / `userMessage` (+ optional `question`) |
| Upload | `POST /upload-url` then `PUT` presigned S3 URL | contentType + fileName |
| Report scam | `POST /reports/scam` | `reportText`, optional `linkedCaseId` |
| Telegram | **Client deep link only** | `https://t.me/CredashieldBot` (no API call from browser) |

Also present on API (not heavily used by current UI): `GET /coverage`, `GET /tactics` (OPTIONS ok; `/coverage` returned 404 on one probe — may be stage/path drift).

---

## 2. Backend map (live Mumbai)

```
Browser (Amplify) ──HTTP──► API Gateway HTTP API (x1ed4uf5q9)
                              │
                              ▼
                         Intake Lambda (creda-mumbai-*)
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
         DynamoDB Cases   SQS WorkerQueue   S3 EvidenceBucket
                              │              (uploads + curated bundle)
                              ▼
                    Worker / gatherer Lambda
                    (deterministic + ATS searcher + forum exhibits)
                              │
                              ▼
                         SQS QwenQueue
                              │
                              ▼
              ECS Fargate creda-qwen-cpu (DesiredCount=1 in template)
                 llama.cpp Qwen3-4B + strands-worker
                              │
                              ▼
                         DynamoDB (verdict, agentPresentation, stream fields)
                              ▲
         EventBridge schedule ─┴─► Ingest / evidence-refresh Lambdas
                                   (daily ATS + forum/advisory snapshots)
```

| Resource | Role today |
|---|---|
| **API Gateway** HTTP API | Routes health, cases, followup, upload-url, reports, telegram webhook |
| **Intake Lambda** | Auth token issue/verify; enqueue; upload URL; reports; telegram webhook |
| **Worker Lambda** | Gather evidence packet; enqueue Qwen; interim status COMPLETED + pending agent |
| **DynamoDB** | Cases, reports (`REPORT#…`), tokens hashed |
| **S3** `creda-mumbai-evidencebucket-*` | Presigned uploads under `cases/uploads/`; curated `bundles/creda-demo-2026-09-17` |
| **SQS WorkerQueue + DLQ** | Case gather |
| **SQS QwenQueue** | Judge tasks (`agentQueueConfigured: true`) |
| **ECS Fargate `creda-qwen-cpu`** | Live judge (llama). Template DesiredCount **1** (warm idle, not scale-to-zero) |
| **ECS EC2 g4dn `creda-qwen-gpu`** | **Not deployed** (template ASG Min/Desired/Max = 1 when shipped) |
| **EventBridge** | Daily ingest schedule (`CredaDailyIngest` / equivalent) + health-refreshed forum/ATS stamps |
| **Lambda evidence-refresh** | Named in `scripts/deploy_all.sh` as `creda-mumbai-evidence-refresh` |
| **Amplify** | Static `index.html` + `app.js` + `styles.css` |
| **Cognito / Step Functions / SNS** | Not on path |

**Repo drift:** Committed `backend/intake/app.py` and `infra/template.yaml` are **thinner** than production. Real Lambda source lives under the Codex `creda-aws-backend` tree referenced by `scripts/deploy_all.sh`.

---

## 3. SEARCHER

| Question | Answer |
|---|---|
| Exists? | **YES** — ATS vacancy index + employer registry + optional live board fetch |
| Connected to Check? | **YES** — runs in gatherer before Qwen; pipelineLog lines on every probed case |
| Open web per request? | **NO** (`openWebPerRequest: false`) |
| Used on a live case? | **YES** — Amazon fee case + Stripe Greenhouse case (2026-09-19 IST afternoon) |
| Follow-up? | **YES** — “Follow-up received: restarting full evidence pipeline” + ATS search again |
| Emits `ev_search_*`? | **Not observed** on these cases; forum exhibits are `ev_forum_*`; vacancy outcomes appear in pipeline text / other evidence checks |

---

## 4. EVENTBRIDGE

| Item | Finding |
|---|---|
| In code/infra | `infra/template.yaml` → `IngestFunction` event `DailyIngest` `Type: Schedule`, name **`CredaDailyIngest`**, default `cron(0 6 * * ? *)` |
| Live now? | **YES functionally** — `forumIngestion: true`, ingest timestamps today; cases cite forum intel |
| What it does | **Daily (and/or refresh-job) allowlisted source refresh**: employer fraud pages, Stripe Greenhouse jobs, advisories → S3 raw/curated signals for the packet. **Not** user reminders. **Not** mid-case rechecks (rechecks are follow-up → re-queue). |
| AWS `events list-rules` | **Not executed** (no `creda-dev` credentials on box) |

---

## 5. GPU path

| Item | Today |
|---|---|
| Cluster | Intended name `creda-qwen-gpu` (template) — **not deployed** |
| Task | vLLM `Qwen/Qwen3-VL-4B-Instruct` + worker sidecar |
| ASG | Template: Min=1 Max=1 Desired=1 (**warm idle**, not scale-to-zero) |
| Live judge | **Fargate `creda-qwen-cpu` DesiredCount=1**, llama.cpp text |
| Fallback story | Docs: Fargate text when GPU unhealthy — GPU not up yet, so Fargate **is** primary |

---

## 6. Data flow — one Check (verified live)

1. User pastes offer (or uploads via `/upload-url` → S3) on Amplify → **Check**.
2. `POST /cases` → Intake writes DynamoDB + enqueues WorkerQueue → returns `caseId` + `accessToken`.
3. Gatherer Lambda: parse → resolve employer → **ATS searcher** (live or cache) → tactic/policy/domain checks → attach **forum** exhibits → write evidence → enqueue **QwenQueue**; UI may already show interim `high_risk` / exhibits.
4. ECS Fargate worker streams llama completion into `agentStreamText` (`STREAMING`) → writes final `verdict`, `headline`, `agentPresentation.blocks`, `agentSource: creda`, `agentStatus: READY`.
5. Amplify poll loop renders **ruling board** (stamp, tactics, exhibits, orders).
6. Optional follow-up → full pipeline restart → new judge pass.
7. Optional report → DynamoDB review item.

**Telegram one-shot (when webhook secret configured):** Telegram → `POST /telegram/webhook` → same case pipeline → bot reply + Amplify deep link `?case=&token=`. Probed unauthorized without secret.

**Live smoke (Amazon fee + WhatsApp):** ~45s to READY, `verdict=high_risk`, `agentSource=creda`, 8 evidence items including policy + forum + channel.

---

## 7. AWS CLI checklist (for operator with `creda-dev`)

```bash
export AWS_PROFILE=creda-dev AWS_DEFAULT_REGION=ap-south-1
aws amplify get-app --app-id d32sg54oqu2gcb
aws apigatewayv2 get-apis
aws events list-rules
aws ecs list-clusters
aws ecs list-services --cluster creda-qwen-cpu
aws ecs describe-services --cluster creda-qwen-cpu --services creda-qwen-cpu
aws lambda list-functions --query "Functions[?contains(FunctionName,'creda')].FunctionName"
# Confirm GPU absent:
aws ecs list-clusters | grep -i gpu || true
```

---

## MVP polish gaps (solid vs half-wired)

**Solid:** Amplify↔API create/poll/report; gather→judge; searcher on path; forum exhibits; Fargate llama judge; multimodal upload API; injection_guard code; EventBridge/daily refresh stamps.

**Half-wired / gaps:** g4dn multimodal not live; Telegram needs secrets/onboarding polish; follow-up clobbers ruling / thin conversationTurns; nextActions sometimes null/strings vs UI objects; live Lambda source not committed here; competing GPU+CPU consumers risk if both desired=1 later; `/coverage` path drift; no open-web searcher.


## Lock (2026-09-19)
**NO multimodal live.** Text-only judge path. Screenshot/PDF/VLM = not ready until g4dn/vLLM ships.
