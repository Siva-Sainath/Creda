# Creda WorkOffer Shield: Astra Composer Plan

**Role:** Astra (staff architect and product planner). This document plans. Composer 2.5 executes.  
**Branch:** `creda/mvp-g4dn-ship`  
**Live UI:** https://main.d32sg54oqu2gcb.amplifyapp.com  
**Live API:** https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com  
**Local mirror:** `/Users/siva/Documents/first_commit_hack`  
**AWS:** profile `creda-dev`, region `ap-south-1`  
**Modes:** `/architect` then `/poteto-mode` on every pack. Do not open a GitHub PR unless the human explicitly asks.

---

## 1. Repo reconnaissance

### 1.1 Branch and GitHub state

| Surface | State |
|---------|-------|
| GitHub branch | `creda/mvp-g4dn-ship` pushed at https://github.com/Siva-Sainath/Creda/tree/creda/mvp-g4dn-ship |
| Local mirror | `/Users/siva/Documents/first_commit_hack` on the same branch |
| Live Amplify | Deployed from `frontend/` with API URL injected at build time |

Every Composer pack starts with a branch guard:

```bash
git branch --show-current   # must print creda/mvp-g4dn-ship
git status -sb              # note uncommitted files before editing
```

### 1.2 Frontend (split SPA)

The UI is no longer a monolith. Real paths:

| Path | Role |
|------|------|
| `frontend/index.html` | Markup shell, view regions, GSAP CDN tags |
| `frontend/styles.css` | Creda mesh palette tokens, layout, kit hand-ports |
| `frontend/app.js` | API client, polling, stage machine, ruling renderers |
| `frontend/amplify.yml` | Build: inject `CREDA_API_URL` into `dist/app.js` |
| `scripts/deploy_all.sh` | SAM deploy, GPU deploy, Amplify dist build |
| `scripts/split_frontend.py` | Historical split tool (already applied) |

Key DOM surfaces on the live page:

- `#view-intake`, `#view-wait`, `#view-result`
- `#stage-rail`, `#browser-wrap` (debug `creda://agent/stream` chrome to delete)
- `.input-channels` (Email | Telegram | DM | Screenshot bar to delete)
- `.composer-shell`, `.liquid-glass`, `#followup-composer`, `#ruling-host`
- `body.creda-baseten` layout class

Palette lock: keep the Creda mesh palette in `:root` (`--bg`, `--bg-mesh-blue`, `--bg-mesh-sage`, `--bg-mesh-teal`, `--ink`, `--blue`, `--risk`, `--safe`). Do not apply a dark tweakcn export. The user rejected that direction.

### 1.3 Backend and judge worker

| Path | Role |
|------|------|
| `backend/intake/app.py` | REST API (create, poll, reports, health) |
| `backend/worker/handler.py` | Legacy Lambda worker (deterministic + Strands explain path to retire) |
| `backend/worker/agent.py` | Bedrock Strands loop (delete from product path) |
| `infra/template.yaml` | SAM stack `creda-mumbai` |
| `infra/qwen-ecs/qwen_worker.py` | ECS SQS worker, Dynamo writes, backend switch |
| `infra/qwen-ecs/judge.py` | Qwen stamp, JSON schema, `_resolve_verdict` |
| `infra/qwen-ecs/vllm_local.py` | vLLM client for g4dn GPU path |
| `infra/qwen-ecs/injection_guard.py` | Prompt injection neutralization |
| `infra/qwen-ecs/presentation.py` | UI presentation blocks |
| `infra/qwen-ecs/media_loader.py` | Screenshot and PDF loading |
| `deploy/bundle/*` | Curated evidence (vacancy index, tactics, employers) |

### 1.4 GPU and fallback infra

| Path | Role |
|------|------|
| `infra/qwen-ecs/template-gpu.yaml` | g4dn.xlarge ASG desired=1, vLLM sidecar + strands-worker |
| `infra/qwen-ecs/template.yaml` | Fargate CPU fallback (`creda-qwen-cpu`, llama.cpp) |
| `scripts/creda_gpu_up.sh` | Scale GPU ASG to desired=1 |
| `scripts/creda_gpu_down.sh` | Scale GPU ASG down when credits are low |
| `scripts/deploy_qwen_gpu_ecs.sh` | Deploy GPU stack |
| `scripts/deploy_qwen_ecs.sh` | Deploy Fargate CPU stack |

vLLM knobs (locked): `Qwen/Qwen3-VL-4B-Instruct`, fp16, `max-model-len 8192`, `max-num-seqs 2`, `QWEN_MAX_TOKENS=200`, temperature 0, thinking disabled, max 2 images, long-edge 1024 px.

### 1.5 Tests and fixtures

| Path | Role |
|------|------|
| `scripts/smoke_mvp.sh` | API health and basic create/poll |
| `scripts/run_test_catalog.sh` | 21-case catalog (`CREDA_TEST_STRICT=true` for no fallback) |
| `scripts/test_injection_fixtures.sh` | DAN and ignore-rules regression |
| `scripts/test_followup.sh` | Follow-up API path |
| `scripts/test_ui_journey.mjs` | Playwright UI journey (extend to 1440 px and 390 px) |
| `scripts/test_e2e_full.sh` | End-to-end API suite |
| `scripts/test_telegram_webhook.sh` | Telegram webhook smoke |
| `scripts/test_cases.json` | Prompt catalog |
| `scripts/fixtures/ocr_scam_offer.png` | Multimodal screenshot fixture |

### 1.6 Branch drift (critical)

**Live API ahead of committed Lambda.** The deployed intake Lambda exposes routes and fields that the branch source does not yet contain:

- Live `/health` reports `judgeMode: creda`, `agentQueueConfigured`, `searcher{...}`, `intakeChannels: [web, extension, telegram]`, `multimodal.uploadUrl`
- Follow-up (`POST /cases/{caseId}/followup`), upload URL, and Telegram routes are deployed but missing from committed `backend/intake/app.py`
- ECS worker reads Dynamo keyed by `caseId`; branch intake still documents `pk/sk` patterns in places
- Live API returns `nextActions` as plain strings in some paths; `frontend/app.js` expects `{label, detail, tone}` objects, which yields empty Next step cards

**Lambda deploy source outside repo.** `scripts/deploy_all.sh` deploys SAM from `/Users/siva/Documents/Codex/2026-09-17/creda-aws-backend/outputs/creda-backend`, not from this repo's `infra/template.yaml`. Pack 1 must pull the deployed Lambda with `aws lambda get-function` and commit the real source here before edits.

**Competing Qwen queue consumers.** Fargate `creda-qwen-cpu` (desired=1) and GPU `creda-qwen-gpu` (desired=1) both poll the same SQS queue. The text-only Fargate worker can grab a screenshot case and ignore images. Fix: Fargate desired=0 by default, scale to 1 only when GPU has zero running tasks for 3 minutes.

**SageMaker leftovers on branch.** `infra/sagemaker/`, `scripts/deploy_sagemaker_judge.sh`, `scripts/wait_and_wire_sagemaker.sh`, `infra/qwen-ecs/sm_inference.py`, `vlm_inference.py`, sagemaker branch in `qwen_worker.py`, and `JudgeBackend: sagemaker` default in `infra/qwen-ecs/template.yaml`. These contradict the "stay deleted" lock.

**Stale docs.** `docs/WAKE_UP_STATUS.md` references Three.js WebGL (`#hero-canvas`). Forbidden. Smoke must assert no `three` script in the built page.

**Frontend doc drift.** Older handoffs cite a monolithic `frontend/index.html`. The live client is `frontend/app.js`.

### 1.7 Notion playbook inventory

Page: https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd

Portable kits and target surfaces:

| Kit | Surface |
|-----|---------|
| Neobrutalism components | Physical ruling stamp and case board |
| ui-layouts Liquid Glass | Judgment shell only (retarget `.liquid-glass`) |
| Animata Bento grid | Exhibit bento, unique slips |
| Berlix flip-card | Tactic tiles (front name, back quoted evidence) |
| React Bits split-text | Headline reveal in `tlVerdict` |
| Lukacho Mock Browser | Official checks wait stage with real careers domain |
| Vercel AI Elements Branch | Follow-up thread under the board |
| Kokonut / Cult UI / Lightswind / 21st.dev / coss origin | Sticky follow-up dock, chips, skeletons, report panel |
| Uiverse / CodePen | Stamp press micro-animation and loaders |
| Creda mesh palette (`frontend/styles.css` `:root`) | Global tokens (not tweakcn dark export) |
| Simple Icons / SVG Repo / Undraw | Icons and idle illustration |
| Excalidraw | Section 4 architecture diagram |
| Screen Studio | Demo recording |

Excluded: unicorn.studio (WebGL), NextBunny, React Native Reusables, Vercel/Supabase/Cloudflare free stack section, Teachable Machine / Groq.

### 1.8 Live UI failures (verified on Amplify)

1. Fixed ~680 to 720 px column in a 1280 px viewport (desktop gutters)
2. Redundant `.input-channels` chip bar under composer
3. Debug `#browser-wrap` with `creda://agent/stream` URL
4. Wait rail jumps to "Writing the ruling" at ~5 s (timer and `agentProgress` driven)
5. Text-heavy results, repeated exhibit paragraphs, thin stamp
6. Follow-up clobbers ruling (verdict resets, Next steps empty)
7. Report panel is inline textarea, not side panel or bottom sheet
8. Non-sticky follow-up on mobile, clipped labels

---

## 2. End-user story (60 seconds, desktop and mobile)

**Persona:** A stressed job seeker receives "Amazon internship, pay kit fee" on Telegram.

**Desktop (>=960 px, 0:00 to 1:00):**

| Time | Action | What they see |
|------|--------|---------------|
| 0:00 | Opens https://main.d32sg54oqu2gcb.amplifyapp.com | Full-width tool on mesh background. Composer hero, no marketing wall. No channel chip bar. |
| 0:05 | Pastes offer text, taps Check | `tlIntake` plays. Stage rail shows Intake, not "Writing the ruling". |
| 0:10 | Waits | `tlEvidence`, `tlSearch`, optional `tlVision` if screenshot attached. Mock browser shows real careers domain, not `creda://`. Each stage >=700 ms dwell. |
| 0:35 | Verdict ready | Physical HIGH RISK stamp slams in. Headline one line. Tactic tiles stagger. Unique exhibit slips in bento grid. Next actions with label and detail. |
| 0:45 | Types "Is the careers link real?" | Searcher bubble appears. Ruling board unchanged. `ev_search_*` exhibit cited. |
| 0:55 | Taps Report a scam | Side panel opens with tactic type and description. Sends. Toast confirms. |

**Mobile (<640 px, same journey):**

| Time | Action | What they see |
|------|--------|---------------|
| 0:00 | Opens site on phone | Full-bleed composer. Targets >=44 px. No horizontal scroll. |
| 0:05 | Paste and Check | Same stage playlist, compressed if API is fast but never skipping to verdict at 5 s. |
| 0:35 | Verdict | Stamp readable. Exhibits stack in bento, no clipped lowercase junk. |
| 0:45 | Follow-up | Sticky bottom follow-up dock. Board stays visible above. |
| 0:55 | Report | Bottom sheet, not buried footer textarea. |

If any step fails, the plan failed.

---

## 3. Diagnosis

### 3.1 Craft and responsive

| Issue | Root cause | Fix direction |
|-------|------------|---------------|
| Cream void, quiet gray type | Baseten rewrite incomplete; mesh palette underused | Keep Creda mesh tokens, stronger contrast, full viewport width |
| ~700 px postcard column | `--col` and `.shell` max-width too narrow | Expand to `--col-wide` (1400 px cap), bleed layouts on desktop |
| Channel chip bar | Legacy `.input-channels` duplicates composer | Delete bar; replace with GSAP `tlIdleExplain` strip |
| Debug stream chrome | `#browser-wrap` bound to `agentStreamText` | Delete chrome; Lukacho mock browser for official checks only |
| Text walls on results | Renderer dumps paragraphs | Ruling board: stamp, tiles, bento slips, orders list |

### 3.2 Functional UI

| Issue | Root cause | Fix direction |
|-------|------------|---------------|
| Wait jump at ~5 s | Worker sets `agentStatus=STREAMING` on first token; UI keys off `agentProgress` strings | Server `agentStage` enum drives playlist with >=700 ms dwell |
| Follow-up clobber | Follow-up restarts pipeline, sets `verdict: pending` | Freeze `rulingSnapshot` on first READY; merge on GET |
| Empty Next step | API returns strings; client expects objects | Normalize on client; emit rich objects from judge |
| Repeated exhibits | Renderer does not dedupe by source URL | Dedupe in presentation layer and UI |
| Non-sticky follow-up | CSS missing sticky/fixed on dock | Breakpoint-specific sticky rules |

### 3.3 Backend and tools

| Issue | Root cause | Fix direction |
|-------|------------|---------------|
| Multimodal not guaranteed | Two workers poll same queue | Fargate desired=0; GPU-only for multimodal cases |
| Searcher index-only | `openWebPerRequest: false` | Run on create and URL or listing follow-ups; emit `ev_search_*` |
| SageMaker path still in code | Leftover scripts and template defaults | git rm leftovers; smoke asserts zero endpoints |
| Bedrock Strands explain | `backend/worker/agent.py` parallel verdict path | Retire to deterministic-only packet feeding Qwen |
| Injection surface | User text treated as instructions | Harden `injection_guard.py`; fixture regression |
| GPU boot fragility | Unpinned vLLM tag, 30 GB root volume | Pin tag, 100 GB gp3 root, host weight cache |

### 3.4 Credits

| Line item | Rate | Daily (24 h) |
|-----------|------|--------------|
| g4dn.xlarge (Mumbai) | $0.579/hr | $13.90 |
| EBS gp3 100 GB | ~$0.012/hr | ~$0.30 |
| Lambda, DynamoDB, SQS, S3, Amplify | bundled | <$0.50 |
| **Total** | | **~$14.7/day** |
| **Runway on ~$238** | | **~16 days** |

Rejected: Fargate CPU always-on at desired=1 adds ~$0.21/hr (~$5/day), cutting runway to ~12 days.

Rejected: SageMaker always-on endpoint (deleted, stay deleted).

Rejected: Spot instances for live judging (reclaim mid-demo).

---

## 4. Target architecture

### 4.1 Diagram (logical)

```
Browser / Telegram / Extension
            |
            v
    API Gateway (HTTP)  creda-mumbai
            |
            v
    Intake Lambda  ------>  DynamoDB (cases, rulingSnapshot, conversationTurns)
            |
            v
         SQS (Qwen queue)
            |
            v
    ECS GPU worker (g4dn, desired=1)  ---->  vLLM Qwen3-VL-4B
            |                                    |
            | (fallback only)                      +--> S3 attachments
            v
    ECS Fargate worker (desired=0, auto-scale on GPU unhealthy)
            |
            v
    llama.cpp Qwen3-4B text-only

Tools (packet only, not verdict):
  - Deterministic checks (domain, fee heuristics)
  - Searcher (vacancy index + listing follow-ups)
  - EventBridge ingest (daily scam feeds)
  - deploy/bundle evidence JSON
```

### 4.2 Verdict authority (Qwen-centered)

Qwen writes: `verdict`, `headline`, `reasoning`, `tactics[]`, `exhibits[]`, `nextActions[]`, uncertainties.

Deterministic checks, searcher, and EventBridge feeds rename their hint field to `ruleHint` in the packet. They do not silently override the model stamp on the product path (hard safety refuse only).

If GPU and Fargate fallback are both down, the UI shows "judge offline, retry". Never a client-invented verdict or API-down mock.

### 4.3 Deletes (enforce in code)

| Delete | Paths |
|--------|-------|
| SageMaker | `infra/sagemaker/`, `scripts/deploy_sagemaker_judge.sh`, `scripts/wait_and_wire_sagemaker.sh`, `infra/qwen-ecs/sm_inference.py`, `vlm_inference.py`, sagemaker branch in `qwen_worker.py` |
| Bedrock Strands loop | `backend/worker/agent.py` product path; `EnableBedrock` wiring in deploy scripts |
| `agentStreamText` to client | Stop writing to Dynamo for UI; remove `#browser-wrap` and stream panel binding in `frontend/app.js` |
| Three.js | Any `#hero-canvas` or `three` script references |
| Debug channel bar | `.input-channels` markup and styles |

### 4.4 Server stage enum

Both Lambda and ECS workers write:

```
agentStage: intake | signals | official_checks | vision | verdict
```

Frontend maps enum to GSAP timelines with >=700 ms minimum dwell per stage. `prefers-reduced-motion` jumps to end state.

### 4.5 Follow-up model

On first READY:

```
rulingSnapshot = { verdict, headline, nextActions, exhibits, tactics, agentPresentation }
```

Follow-up POST appends `conversationTurns[]` only. Never overwrites `verdict`, `headline`, or `nextActions` on the stored item. GET merges snapshot + turns for the UI.

---

## 5. Phased plan

### Phase 1: Efficient backend / Qwen warm path

**Goal:** One multimodal judge path on warm g4dn, Fargate fallback at desired=0, real Lambda source committed, SageMaker deleted.

**Dependencies:** AWS profile `creda-dev`, g4dn quota in ap-south-1.

**Done when:**

- Deployed Lambda source committed to `backend/intake/`
- GPU ASG desired=1, vLLM health passes
- Fargate desired=0 with CloudWatch alarm scale-up
- SageMaker files removed; endpoint count = 0
- `agentStage` enum written by worker
- `rulingSnapshot` frozen on READY
- Searcher runs on create and listing follow-ups

**Pack:** `PACK_1_backend_qwen_warm.md`

### Phase 2: Artistic responsive shell

**Goal:** Full-width desktop layout, mobile bleed, Creda mesh palette, delete channel bar and debug chrome, split `motion.js` for GSAP timelines.

**Dependencies:** Phase 1 API fields stable.

**Done when:**

- Desktop >=960 px uses full useful width
- Mobile <640 px full-bleed, >=44 px targets, no clipped labels
- `.input-channels` removed
- `#browser-wrap` debug chrome removed
- Sticky follow-up dock (desktop) and bottom dock (mobile)
- Report side panel (desktop) and bottom sheet (mobile)
- No `three` script in built page

**Pack:** `PACK_2_artistic_responsive_shell.md`

### Phase 3: GSAP wait + visual result board

**Goal:** Server-driven wait playlist, visual ruling board, follow-up preserves board.

**Dependencies:** Phase 2 shell and Phase 1 `agentStage`.

**Done when:**

- Timelines `tlIdleExplain`, `tlIntake`, `tlEvidence`, `tlSearch`, `tlVision`, `tlVerdict` wired
- >=700 ms dwell per stage; no jump to "Writing the ruling" at 5 s
- Physical stamp with contrast; tactic tiles; bento exhibits deduped
- `nextActions` never empty after follow-up
- Follow-up thread under board; ruling text identical before and after

**Pack:** `PACK_3_gsap_wait_result_board.md`

### Phase 4: Telegram, deploy, smoke

**Goal:** Telegram onboarding CTA, Amplify deploy, full verification loop green.

**Dependencies:** Phases 1 through 3.

**Done when:**

- Telegram CTA <=3 steps from UI
- `scripts/verify_full_loop.sh` passes green
- `test_ui_journey.mjs` passes at 1440 px and 390 px
- Cost line printed in verify output

**Pack:** `PACK_4_telegram_deploy_smoke.md`

### Optional one-shot

**Pack:** `PACK_5_one_shot_full_mvp.md` (all phases in one session if context allows)

---

## 6. Composer execution packs

Verbatim packs live in separate files. Paste one pack at a time into Composer 2.5.

| Pack | File | Phase |
|------|------|-------|
| 1 | `PACK_1_backend_qwen_warm.md` | Backend / Qwen warm path |
| 2 | `PACK_2_artistic_responsive_shell.md` | Responsive shell |
| 3 | `PACK_3_gsap_wait_result_board.md` | GSAP wait + result board |
| 4 | `PACK_4_telegram_deploy_smoke.md` | Telegram + deploy + smoke |
| 5 | `PACK_5_one_shot_full_mvp.md` | Full MVP one-shot |

Shared locks in every pack:

- Branch `creda/mvp-g4dn-ship`
- No GitHub PR unless human asks
- SageMaker stay deleted
- `/architect` then `/poteto-mode`
- Notion playbook hand-ports only (no npm UI kits)
- Creda mesh palette (no dark tweakcn theme)

---

## 7. Efficiency notes (top 5)

1. **Warm g4dn only for multimodal.** One GPU instance at desired=1 (~$0.579/hr). Fargate text at desired=0 saves ~$5/day versus always-on CPU worker.

2. **Tiny Qwen completions.** `max_tokens=200`, temperature 0, no chain-of-thought. Cap images at 2, long-edge 1024 px. Largest token savings on the hot path.

3. **Delete SageMaker and Bedrock Strands.** Idle SageMaker and 800-token Bedrock loops burn credits without user value. Qwen owns the stamp.

4. **Searcher on intent, not every poll.** Run index search on create and on follow-ups with URL or listing intent. Skip redundant calls.

5. **Stop shipping debug stream to client.** Removing `agentStreamText` Dynamo writes and the mock-browser panel cuts Dynamo write costs and frontend complexity.

---

## Verification loop spec: `scripts/verify_full_loop.sh`

Composer must create this script. It orchestrates existing tests plus new assertions. Exit non-zero on any failure.

### Environment

```bash
export AWS_PROFILE="${AWS_PROFILE:-creda-dev}"
export CREDA_API_URL="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
export CREDA_UI_URL="${CREDA_UI_URL:-https://main.d32sg54oqu2gcb.amplifyapp.com}"
export CREDA_TEST_STRICT=true
```

### Steps (in order)

| Step | Command / check | Pass condition |
|------|-----------------|----------------|
| 1 | `curl -s "$CREDA_API_URL/health" \| jq .` | `ok: true`, `judgeMode: creda`, `dataReady: true` |
| 2 | AWS ECS describe GPU service | Running task count = 1 |
| 3 | vLLM health via internal ALB or worker health gate | HTTP 200 |
| 4 | `aws sagemaker list-endpoints --region ap-south-1` | Count = 0 |
| 5 | `bash scripts/smoke_mvp.sh` | Exit 0 |
| 6 | `CREDA_TEST_STRICT=true bash scripts/run_test_catalog.sh` | Exit 0, no `agentSource: fallback` |
| 7 | `bash scripts/test_injection_fixtures.sh` | Exit 0, verdict not flipped by DAN |
| 8 | Extended `bash scripts/test_followup.sh` | Stored `verdict` and `headline` unchanged after "Is the careers link real?"; `ev_search_*` exhibit present |
| 9 | Create case with `scripts/fixtures/ocr_scam_offer.png` | Poll until `agentSource` shows creda-vlm or vllm |
| 10 | `bash scripts/test_telegram_webhook.sh` | Exit 0 or skip with logged reason if webhook not deployed |
| 11 | `node scripts/test_ui_journey.mjs` at 1440 px and 390 px | No `creda://` text; `#ruling-host` text identical before/after follow-up; next-steps non-empty; exhibit titles unique; follow-up dock sticky; no horizontal overflow |
| 12 | Built page grep | No `three` script tag |
| 13 | Print cost line | `g4dn $0.579/hr, ~$14.7/day, ~16 days on $238` |

### Browser checklist (manual if Playwright skipped)

At 1440 px and 390 px on the live UI:

- [ ] No `creda://` visible anywhere
- [ ] No `.input-channels` bar
- [ ] Wait stages dwell, no 5 s jump to "Writing the ruling"
- [ ] Stamp readable (HIGH RISK / CLEAR / NEEDS REVIEW)
- [ ] Next steps list never empty
- [ ] Exhibit titles unique (no repeated Amazon paragraph)
- [ ] Follow-up dock sticky or fixed at bottom on mobile
- [ ] Report opens as side panel (desktop) or bottom sheet (mobile)
- [ ] Ruling board unchanged after follow-up

### Done signal

The MVP is ready for demo only when `scripts/verify_full_loop.sh` exits 0 and the human can run the 60-second user story on phone and laptop without failure.

---

## References

| Document | Path |
|----------|------|
| Astra handoff | `docs/CREDA_GPT_ASTRA_FULL_HANDOFF.md` |
| g4dn architect note | `docs/ARCHITECT_G4DN_NOTE.md` |
| MVP ship brief | `docs/CREDA_CURSOR_MVP_SHIP_G4DN.md` |
| Telegram setup | `docs/TELEGRAM_SETUP.md` |
| Verify iterate loop | `docs/CREDA_CURSOR_ITERATE_GROK_VERIFY_LOOP.md` |
| Design resources | `docs/design/resources.md` |
| Notion playbook | https://app.notion.com/p/Hackathons-Playbook-2d1bb100e6d2806d9182d2c324b42afd |

*Version: 2026-09-19. Branch: creda/mvp-g4dn-ship. Planner: Astra. Executor: Composer 2.5.*
