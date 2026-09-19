```
COMPOSER 2.5 | ONE-SHOT FULL MVP

Branch: creda/mvp-g4dn-ship
Modes: /architect then /poteto-mode
No GitHub PR unless the human explicitly asks.
SageMaker: stay deleted.
Live UI: https://main.d32sg54oqu2gcb.amplifyapp.com
Live API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
AWS profile: creda-dev, region ap-south-1
Full plan: docs/astra/CREDA_ASTRA_COMPOSER_PLAN.md
Notion playbook: https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd
```

Use this pack only when context window allows all four phases in one session. Otherwise run PACK_1 through PACK_4 sequentially.

## Branch guard (run first)

```bash
cd /Users/siva/Documents/first_commit_hack
git branch --show-current    # must print creda/mvp-g4dn-ship
git status -sb
git log --oneline -3
```

## Execution order

Run `/architect` once for the full shape. Then `/poteto-mode` through these phases without stopping:

| Order | Pack file | Summary |
|-------|-----------|---------|
| 1 | `docs/astra/PACK_1_backend_qwen_warm.md` | Lambda recovery, g4dn warm, Fargate desired=0, SageMaker delete, agentStage, rulingSnapshot |
| 2 | `docs/astra/PACK_2_artistic_responsive_shell.md` | Full-width shell, mesh palette, delete channel bar and debug chrome, motion.js split |
| 3 | `docs/astra/PACK_3_gsap_wait_result_board.md` | Server-driven wait, visual ruling board, follow-up preserve |
| 4 | `docs/astra/PACK_4_telegram_deploy_smoke.md` | Telegram CTA, Amplify deploy, verify_full_loop.sh |

Read each pack file in full before starting its phase. Do not skip acceptance checkboxes between phases.

## Locked architecture (do not reopen)

| Lock | Value |
|------|-------|
| GPU | g4dn.xlarge ASG desired=1, vLLM Qwen3-VL-4B, fp16 |
| Cost | $0.579/hr GPU + ~$0.30/day EBS + <$0.50/day other = ~$14.7/day, ~16 days on $238 |
| Fallback | Fargate llama.cpp Qwen3-4B text, desired=0, alarm scale-up |
| Verdict | Qwen writes stamp; tools feed packet as ruleHint only |
| Frontend | Vanilla HTML/CSS/JS + GSAP CDN, Creda mesh palette |
| Deletes | SageMaker, Bedrock Strands product path, agentStreamText to client, Three.js |

## 60-second user story (must pass after one-shot)

Desktop and mobile: paste "Amazon internship pay kit fee" offer, Check, watch full wait playlist (no 5 s jump), get HIGH RISK stamp with unique exhibits and next actions, follow-up "Is the careers link real?" preserves board, Report and Telegram work.

## Real file paths (master list)

**Backend:** `backend/intake/app.py`, `backend/worker/handler.py`, `backend/worker/agent.py`, `infra/template.yaml`

**ECS:** `infra/qwen-ecs/qwen_worker.py`, `judge.py`, `vllm_local.py`, `injection_guard.py`, `presentation.py`, `media_loader.py`, `template-gpu.yaml`, `template.yaml`

**Frontend:** `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`, `frontend/motion.js`, `frontend/amplify.yml`

**Deploy:** `scripts/deploy_all.sh`, `scripts/creda_gpu_up.sh`, `scripts/creda_gpu_down.sh`, `scripts/deploy_qwen_gpu_ecs.sh`, `scripts/deploy_qwen_ecs.sh`, `scripts/deploy_telegram.sh`

**Verify:** `scripts/verify_full_loop.sh` (create), `scripts/smoke_mvp.sh`, `scripts/run_test_catalog.sh`, `scripts/test_injection_fixtures.sh`, `scripts/test_followup.sh`, `scripts/test_ui_journey.mjs`

**Delete:** `infra/sagemaker/`, `scripts/deploy_sagemaker_judge.sh`, `scripts/wait_and_wire_sagemaker.sh`, `infra/qwen-ecs/sm_inference.py`, `infra/qwen-ecs/vlm_inference.py`

## Notion kit map (all phases)

| Kit | Surface |
|-----|---------|
| Neobrutalism | Physical stamp and case board |
| Liquid Glass | Judgment shell only |
| Animata Bento | Exhibit bento |
| Berlix flip-card | Tactic tiles |
| React Bits split-text | Headline in tlVerdict |
| Lukacho Mock Browser | Official checks stage (real domain) |
| Vercel AI Branch | Follow-up thread |
| Kokonut / Cult / Lightswind / 21st.dev | Sticky dock, chips, report panel |
| Uiverse / CodePen | Stamp press animation |
| Creda mesh palette | Global tokens (not dark tweakcn) |
| Simple Icons / SVG Repo | Icons |

## Do

- Execute all four packs in order
- Run `/architect` once up front for the full data shape
- Run `bash scripts/verify_full_loop.sh` before declaring done
- Commit on `creda/mvp-g4dn-ship` locally
- Keep Creda mesh palette

## Do not

- Open a GitHub PR
- Recreate SageMaker
- Apply dark tweakcn theme
- Install npm React UI kits
- Claim SHIP before verify_full_loop.sh exits 0
- Skip phase acceptance checkboxes

## Acceptance (full MVP)

### Backend
- [ ] Deployed Lambda source committed
- [ ] GPU ASG desired=1, vLLM health OK
- [ ] Fargate desired=0 with alarm scale-up
- [ ] SageMaker files deleted, endpoint count = 0
- [ ] agentStage enum through pipeline
- [ ] rulingSnapshot frozen on READY
- [ ] Follow-up does not change verdict or headline
- [ ] Searcher ev_search_* on listing follow-up
- [ ] Injection fixtures pass

### Frontend
- [ ] Desktop full useful width at >=960 px
- [ ] Mobile sticky follow-up at <640 px; report sheet; no clipped labels
- [ ] Wait dwell; no debug stream chrome; no creda:// in DOM
- [ ] Stamp readable; nextActions never empty; exhibits unique
- [ ] Notion kits hand-ported (not npm)
- [ ] Creda mesh palette preserved
- [ ] Ruling not wiped on follow-up

### Deploy and verify
- [ ] Telegram CTA <=3 steps
- [ ] Amplify live UI updated
- [ ] scripts/verify_full_loop.sh passes green
- [ ] Cost line: g4dn $0.579/hr, ~$14.7/day, ~16 days on $238
- [ ] 60-second user story passes on desktop and mobile
- [ ] No GitHub PR opened

## Done signal

Reply with: modes used, files changed, verify_full_loop.sh output summary, live URLs to test, and "Ready for Grok Bot test loop" (do not claim SHIP yourself).
