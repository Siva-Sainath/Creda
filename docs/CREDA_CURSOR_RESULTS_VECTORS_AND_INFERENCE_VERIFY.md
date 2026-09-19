# CURSOR — Fix blank stamp + vector results UI + confirm Qwen path

**Modes:** `/architect` then `/poteto-mode`

Live UI: https://main.d32sg54oqu2gcb.amplifyapp.com/
API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
Edit `frontend/index.html` (vanilla + GSAP). Deploy Amplify. No PR unless asked.

## Verified infra (re-check and print — do not guess)
Grok Bot verified with `aws --profile creda-dev --region ap-south-1`:

| Fact | Value |
|------|--------|
| SageMaker endpoint | `creda-qwen-judge` **InService** |
| Model | `hf-vlm-qwen3-5-4b-…` (Qwen3.5-4B VLM via vLLM SageMaker image) |
| Instance | **ml.g5.xlarge** × 1 |
| ECS | `creda-qwen-cpu` service running task def `:23` |
| Live judge path | `JUDGE_BACKEND=sagemaker` + `SAGEMAKER_ENDPOINT_NAME=creda-qwen-judge` |
| Fallback present | `LLAMA_URL=http://127.0.0.1:8080/...` only if backend flipped to `llama` |

**Re-verify and paste:**
```bash
aws --profile creda-dev --region ap-south-1 sagemaker describe-endpoint --endpoint-name creda-qwen-judge --query EndpointStatus
aws --profile creda-dev --region ap-south-1 ecs describe-task-definition --task-definition creda-qwen-cpu:23 \
  --query 'taskDefinition.containerDefinitions[].environment[?name==`JUDGE_BACKEND` || name==`SAGEMAKER_ENDPOINT_NAME`]'
```
Create one live case and confirm logs/response show SageMaker invoke (not local llama).

**UI implication:** optimize wait choreography for **GPU SageMaker** latency. Do not assume 30–70s CPU llama waits. Keep compressed ≥700ms/scene so humans still see stages.

---

## P0 UI from live screenshot

### 1) Blank stamp (text overlay missing)

**ROOT CAUSE (Grok Bot live browser, 2026-09-19):**
- SVG already contains tspans HIGH / RISK (aria-label HIGH RISK stamp).
- Animation `.stampInkPress` ends at `opacity: 1` on `.stamp-ink`.
- That overrides the inner fill rect `opacity=".1"`, so the rect paints solid currentColor (e.g. #b42318 for risk).
- Text is the same currentColor → invisible on solid fill.
- Side chip HIGH RISK is also nearly invisible (~9px #5f6d7a on a pale chip).

**Fix (required):**
1. Do not animate opacity to 1 on the filled stamp rect. Keep fill at ~0.08–0.15 opacity, or animate only stroke / transform.
2. Split classes: `.stamp-fill` (low opacity) vs `.stamp-text` (opacity 1, never faded by the fill keyframe).
3. Ensure stamp text contrast: dark ink on light wash, OR white/cream text on solid risk fill — never same-color-on-same-color.
4. Make the adjacent verdict chip readable (larger type, stronger contrast) as backup.
5. Also remove/override `body.creda-baseten` rules that set `backdrop-filter: none` and flatten `.liquid-glass` on the results board.


### 2) Results too text-heavy — vectors that explain
Judges should *see* why it is a scam.

Each matched tactic → compact **visual tile** (icon + 1 line), not a paragraph card:

| Signal | Vector look |
|--------|-------------|
| Upfront fee / laptop deposit | Wallet → ban / coins leaving phone (brief GSAP) |
| Telegram / WhatsApp-only offer | Chat bubble + cracked shield |
| No official careers URL | Broken link vs green careers check |
| Lookalike domain | Side-by-side domain pills, mismatch pulse |
| Missing employer proof | Empty ID card, dashed "needs verify" |

Rules:
- One short "Why Creda ruled" sentence; long prose behind Details.
- Exhibits E1–E4 stagger; flip only with real provenance.
- `prefers-reduced-motion` respected.
- Still Ruling + Exhibits tool — not a marketing landing.

### 3) Do not regress
No cream 24px grid; keep glass + flow bg if present; compact Telegram; always `X-Case-Token`; no `evidence is not defined`.

---

## Done checklist
1. `/architect` SM vs ECS proof (paste AWS)
2. Screenshot: stamp with visible text
3. Screenshot: vector tactic tiles
4. Amplify hard-refresh note
5. Live case confirms SageMaker path
6. Ready for Grok Bot test loop
