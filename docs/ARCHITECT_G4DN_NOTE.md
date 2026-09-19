# Architect note — Creda MVP g4dn ship (2026-09-19)

## Current state map

| Component | Today | Target |
|-----------|-------|--------|
| SageMaker `creda-qwen-judge` | Deleted | Stay deleted |
| Fargate `creda-qwen-cpu` | `JUDGE_BACKEND=llama`, llama.cpp sidecar | Text fallback when GPU unhealthy |
| GPU ECS | **Not deployed** | `g4dn.xlarge` ASG desired=1, vLLM + worker |
| Verdict authority | Lambda `compute_verdict` + judge explain-only | Model stamp + schema validate; deterministic only on parse fail / hard safety |
| Forum ingest | EventBridge daily, 6 sources | Add `eventbridge_feed` exhibit id in packet |
| Reports | `POST /reports/scam` | Extend `tacticType`, `evidenceUrls`, EventBridge `creda.scam.reported` |
| Telegram | Webhook exists, optional | Compact 3-step onboarding in UI |
| Frontend | build 54, 720px column, follow-up clobber | Full width, dwell wait, preserve ruling on follow-up |

## g4dn quota

`g4dn.xlarge` offered in `ap-south-1a/b/c`. Service quota CLI returned `0` (may mean unlimited default or account-specific). **Smoke:** `creda_gpu_up.sh` → ASG launch → vLLM `/health`.

## Cost

**~$0.579/hr** idle on g4dn.xlarge Mumbai. ~$238 credits ≈ **410 hours (~17 days)** always-on.

## Implementation order (this branch)

1. `infra/qwen-ecs/template-gpu.yaml` + `scripts/creda_gpu_{up,down}.sh` + `deploy_qwen_gpu_ecs.sh`
2. `vllm_local.py` + worker `JUDGE_BACKEND=vllm` + health gate
3. `judge.py` centerpiece JSON + `injection_guard.py`
4. Lambda: `rulingSnapshot` on follow-up; GET merge; reports + EventBridge
5. Frontend: width, wait dwell, follow-up preserve, demo chips, stamp, nextActions normalize
6. `scripts/test_injection_fixtures.sh`

## Not in scope

- GitHub PR
- Marketing landing rewrite
- SageMaker recreation
- Spot instances for live judge
