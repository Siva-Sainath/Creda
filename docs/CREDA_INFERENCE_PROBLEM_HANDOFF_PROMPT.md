# Handoff prompt — Creda inference cost vs latency (paste to another LLM)

You are advising on AWS inference architecture for **Creda WorkOffer Shield**, a job-offer scam checker (WeMakeDevs hackathon / MVP).

## Product pipeline (important)
Creda is **not** “LLM decides the verdict.”

1. **Intake** → API Gateway → Lambda  
2. **Deterministic rules** (domains, fee tactics, ATS vacancy index, policies) set the **verdict** (`high_risk` | `unverified` | `no_conflict_found`) in ~**1 second**  
3. A **judge worker** then writes the **headline / explanation / presentation** (and may fill nextActions). That is the slow part users wait on in the UI.  
4. UI polls until `agentStatus=READY`.

So the “inference problem” is mostly: **make explanation generation fast and cheap**, without burning ~$250 of credits on idle GPU.

## Current infra (ap-south-1, account used for Creda)
- Frontend: Amplify `https://main.d32sg54oqu2gcb.amplifyapp.com/`  
- API: `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`  
- Judge queue → ECS service **`creda-qwen-cpu`** (Fargate), task runs worker + optional **llama.cpp** sidecar  
- Env switch: `JUDGE_BACKEND=sagemaker | llama`  
- SageMaker JumpStart-style endpoint was **`creda-qwen-judge`** on **`ml.g5.xlarge`**, model family **Qwen3.5-4B VLM** (vLLM image). As of 2026-09-19 the endpoint was **deleted / not found** (good for cost).  
- Budget: ~**$250** AWS credits.

## Measured latency (live, 2026-09-19)
Fresh API polls today:

| Case | Rules verdict | Time to `agentStatus=READY` (explanation) |
|------|----------------|---------------------------------------------|
| Amazon fee / Telegram | `high_risk` @ ~1s | **~35s** (`agentSource=creda`) |
| Vague / no fee | `unverified` @ ~1s | **~21s** |

**Practical average for ECS explanation path right now: ~25–35 seconds** end-to-end to READY (rules almost instant; judge is the wait).

Historical smoke table (earlier CPU/qwen docs, includes queue):

| Case | Total ~ |
|------|---------|
| Stripe clean | ~18s |
| Injection | ~19s |
| Amazon fee | ~30s |
| Lookalike (queued) | ~70s |

CPU llama.cpp noted at ~**2–3 tokens/s**; every extra completion token adds ~0.3–0.5s. `QWEN_MAX_TOKENS` often ~200–256.

UI wait feels boring because users stare at a weak loader for that 20–40s.

## The cost problem with SageMaker JumpStart / real-time endpoints
**Real-time SageMaker endpoints bill instance-hours while InService — even at zero traffic.**

- `ml.g5.xlarge` hosting ≈ **$1.40/hr** → ≈ **$1,000/month** always-on  
- **$250 credits ≈ 170–180 GPU hours** (~7–8 days continuous, or ~6 hrs/day for a month)  
- There is **no true “standby / idle = $0” mode** for a classic real-time endpoint. “Idle” still pays.

### Ways to incur *less* cost on SageMaker (options to evaluate)
1. **Delete the endpoint when not demoing** (what Creda did) — $0 GPU, users on ECS CPU.  
2. **Schedule start/stop** (EventBridge → create/update endpoint or ASG desired capacity) only for hackathon / judging windows.  
3. **Async inference** with scale-to-zero — same $/hr when warm, but can scale to 0 between bursts (cold start minutes). OK for batch, awkward for interactive UI.  
4. **Serverless Inference** — pay per use, but **CPU-oriented / limited GPU story**; often a poor fit for 4B VLM.  
5. **Multi-model endpoint / smaller instance** — still always-on unless deleted; savings limited.  
6. **Spot / capacity provider on ECS+EC2 GPU** (not JumpStart SM) — cheaper turbo for demos; reclaim risk.  
7. **Do not** keep JumpStart real-time `InService` “just in case” — that is the budget killer.

**Bottom line:** JumpStart doesn’t give free standby. To save money you must **not leave a real-time GPU endpoint up**.

## Desired architecture tradeoff (what we want advice on)
Design a recommendation for Creda with constraints:

1. **Always-on path ≤ ~$250/mo** (ideally much less): ECS Fargate + llama.cpp Qwen 4B-class GGUF, short JSON outputs, warm server.  
2. Target explanation latency: ideally **p50 &lt; 15s**, acceptable **p95 &lt; 40s** on CPU; optional **GPU turbo** only when scheduled.  
3. Verdict must stay **rule-locked** (injection cannot flip stamp); LLM only explains.  
4. UI will add wait-loop storytelling for the slow window — don’t pretend latency is zero.  
5. Compare options: ECS-CPU only vs scheduled SM JumpStart vs ECS-on-g5 vs Bedrock (currently `bedrockEnabled:false`).

## Ask
Please propose:
1. Best default inference path for the $250 budget  
2. Exact ops playbook to keep SageMaker cost at $0 when idle (delete vs stop vs async scale-to-zero — be precise)  
3. Concrete knobs to cut ECS latency (quant, max tokens, batch, task CPU/memory, warm-up, queue concurrency)  
4. Whether JumpStart is worth it at all for a hackathon MVP vs ECS-only  
5. A simple cost table: always-on SM g5 vs ECS Fargate vs 4h/day scheduled GPU  

Be specific to **ap-south-1**, Qwen ~4B, interactive case checks (not batch).
