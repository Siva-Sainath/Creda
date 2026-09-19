```
COMPOSER 2.5 | Phase 1: Efficient backend / Qwen warm path

Branch: creda/mvp-g4dn-ship
Modes: /architect then /poteto-mode
No GitHub PR unless the human explicitly asks.
SageMaker: stay deleted.
Live API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
AWS profile: creda-dev, region ap-south-1
Notion playbook: https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd
```

## Branch guard (run first)

```bash
cd /Users/siva/Documents/first_commit_hack
git branch --show-current    # must print creda/mvp-g4dn-ship
git status -sb
git ls-files backend/intake/app.py infra/qwen-ecs/qwen_worker.py
```

If not on `creda/mvp-g4dn-ship`, check out that branch before any edit.

## Goal

Commit the real deployed Lambda source. Warm g4dn multimodal judge with vLLM. Fargate text fallback at desired=0. Delete SageMaker leftovers. Add `agentStage` enum and `rulingSnapshot` follow-up model. Wire searcher on create and listing follow-ups.

## Real file paths

| Area | Paths |
|------|-------|
| Intake API | `backend/intake/app.py`, `backend/intake/shared/` |
| Legacy worker | `backend/worker/handler.py`, `backend/worker/agent.py`, `backend/worker/deterministic.py` |
| SAM | `infra/template.yaml`, `infra/samconfig.toml.example` |
| ECS worker | `infra/qwen-ecs/qwen_worker.py`, `judge.py`, `vllm_local.py`, `injection_guard.py`, `presentation.py`, `media_loader.py` |
| GPU stack | `infra/qwen-ecs/template-gpu.yaml` |
| Fargate stack | `infra/qwen-ecs/template.yaml` |
| Deploy | `scripts/deploy_all.sh`, `scripts/deploy_qwen_gpu_ecs.sh`, `scripts/deploy_qwen_ecs.sh`, `scripts/creda_gpu_up.sh`, `scripts/creda_gpu_down.sh` |
| Delete targets | `infra/sagemaker/`, `scripts/deploy_sagemaker_judge.sh`, `scripts/wait_and_wire_sagemaker.sh`, `infra/qwen-ecs/sm_inference.py`, `infra/qwen-ecs/vlm_inference.py` |
| Tests | `scripts/smoke_mvp.sh`, `scripts/test_followup.sh`, `scripts/test_injection_fixtures.sh` |
| Evidence | `deploy/bundle/vacancy_index.jsonl`, `deploy/bundle/` |

## Step 1: Recover deployed Lambda source

The live API is ahead of committed source. Pull and commit before edits.

```bash
aws lambda get-function --function-name creda-mumbai-intake \
  --region ap-south-1 --profile creda-dev \
  --query 'Code.Location' --output text
# Download zip, diff against backend/intake/, commit the real routes:
# POST /cases/{caseId}/followup, POST /upload-url, Telegram handlers
```

Update `scripts/deploy_all.sh` to deploy from this repo's `infra/template.yaml`, not the external Codex path.

## Step 2: Delete SageMaker (git rm)

```bash
git rm -r infra/sagemaker/
git rm scripts/deploy_sagemaker_judge.sh scripts/wait_and_wire_sagemaker.sh
git rm infra/qwen-ecs/sm_inference.py infra/qwen-ecs/vlm_inference.py
```

Remove the `sagemaker` backend branch from `infra/qwen-ecs/qwen_worker.py`. Change `JudgeBackend` default in `infra/qwen-ecs/template.yaml` to `llama`.

Remove SageMaker deploy steps from `scripts/deploy_all.sh`.

Assert after deploy:

```bash
aws sagemaker list-endpoints --region ap-south-1 --profile creda-dev --query 'length(Endpoints)'
# must be 0
```

## Step 3: GPU warm path (g4dn desired=1)

Edit `infra/qwen-ecs/template-gpu.yaml`:

- ASG min/max/desired = 1 on `g4dn.xlarge`
- Pin vLLM image tag (do not use `:latest`)
- Add 100 GB gp3 root volume on launch template
- Host weight cache bind mount with `--download-dir`
- `--limit-mm-per-prompt image=2`
- Env: `QWEN_MAX_TOKENS=200`, temperature 0, thinking disabled

Edit `infra/qwen-ecs/vllm_local.py` and `media_loader.py`:

- Resize images to long-edge <=1024 before send
- Max 2 images per case

Deploy:

```bash
bash scripts/creda_gpu_up.sh
bash scripts/deploy_qwen_gpu_ecs.sh
```

Verify vLLM health before SQS consume in `qwen_worker.py`.

Cost comment in `scripts/creda_gpu_up.sh`:

```
# g4dn.xlarge Mumbai ~$0.579/hr, ~$14.7/day all-in, ~16 days on $238 credits
```

## Step 4: Fargate fallback desired=0

Edit `infra/qwen-ecs/template.yaml`:

- Set ECS service desired count default to 0
- Add CloudWatch alarm on GPU service running task count = 0 for 3 minutes
- EventBridge rule to scale Fargate service to desired=1 on alarm
- Scale back to 0 when GPU healthy

Only one consumer should poll multimodal cases. GPU worker owns screenshot and PDF cases.

## Step 5: Retire Bedrock Strands on product path

In `backend/worker/handler.py`:

- Remove `strands_explain` call from the product verdict path
- Keep deterministic checks as packet annotations only
- Rename deterministic verdict field to `ruleHint` in the packet sent to Qwen

In `infra/template.yaml`:

- Confirm `EnableBedrock=false` in deploy parameter overrides

Delete or gate `backend/worker/agent.py` so it is not invoked on the live case path.

## Step 6: agentStage enum

In `infra/qwen-ecs/qwen_worker.py` and `backend/worker/handler.py`, write to Dynamo:

```
agentStage: intake | signals | official_checks | vision | verdict
```

At each pipeline step, before Qwen call. Remove reliance on `agentProgress` free-text strings for UI stage mapping.

Stop writing `agentStreamText` to Dynamo. Remove SET/REMOVE of `agentStreamText` in `qwen_worker.py`.

## Step 7: rulingSnapshot and follow-up

In intake Lambda (`backend/intake/app.py`):

- On first READY, freeze `rulingSnapshot` with verdict, headline, nextActions, exhibits, tactics, agentPresentation
- Follow-up POST appends to `conversationTurns[]` only
- Never set `verdict: pending` or restart pipeline on follow-up
- GET merges `rulingSnapshot` + `conversationTurns` for the client

Emit `nextActions` as objects `{label, detail, tone}`, not plain strings.

## Step 8: Searcher wiring

On case create and on follow-ups containing a URL or listing/careers/real intent:

- Run vacancy index search against `deploy/bundle/vacancy_index.jsonl`
- Emit one citeable exhibit `ev_search_*` with source URL, excerpt, fetched_at
- Add `eventbridge_feed` exhibit from last ingest (`backend/ingest/handler.py` daily cron)

Do not claim live web search. Index-only with honest labeling.

## Step 9: Injection hardening

Confirm `infra/qwen-ecs/injection_guard.py` strips DAN and ignore-rules prefixes before packet merge.

Run:

```bash
bash scripts/test_injection_fixtures.sh
```

## Do

- Pull deployed Lambda before editing intake
- Pin vLLM Docker tag and expand root volume
- Set Fargate desired=0 with alarm-based scale-up
- Write `agentStage` at each worker step
- Freeze `rulingSnapshot` on READY
- git rm all SageMaker files
- Document $/hr in deploy script comments

## Do not

- Recreate SageMaker endpoints
- Leave Fargate and GPU both at desired=1 polling the same queue
- Deploy from the external Codex backend path
- Open a GitHub PR
- Write `agentStreamText` to Dynamo for the UI
- Let deterministic checks override Qwen verdict on the product path

## Acceptance

- [ ] `git branch --show-current` is `creda/mvp-g4dn-ship`
- [ ] Deployed intake routes committed in `backend/intake/app.py`
- [ ] SageMaker endpoint count = 0; SageMaker files removed from repo
- [ ] GPU ASG desired=1; vLLM `/health` returns 200
- [ ] Fargate service desired=0 by default; scales up only on GPU alarm
- [ ] Smoke case with screenshot reaches `agentSource` vllm or creda-vlm
- [ ] `agentStage` written through full pipeline
- [ ] `rulingSnapshot` present on READY cases
- [ ] Follow-up does not change stored verdict or headline
- [ ] Searcher emits `ev_search_*` on listing follow-up
- [ ] `bash scripts/test_injection_fixtures.sh` passes
- [ ] g4dn warm path $/hr documented (~$0.579/hr, ~$14.7/day, ~16 days on $238)
- [ ] No GitHub PR opened
