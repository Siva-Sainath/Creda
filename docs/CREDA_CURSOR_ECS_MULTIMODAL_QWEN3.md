# CURSOR — Get ECS multimodal Qwen3 working (cheap, warm, good enough)

**Modes:** `/architect` then `/poteto-mode`

Repo: `/Users/siva/Documents/first_commit_hack`  
AWS: `creda-dev` · `ap-south-1`  
API: `https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com`  
No PR unless asked.

## Goal
Ship **one warm ECS judge** that:
1. Runs a **Qwen3-family multimodal** model (vision + text) for screenshots / PDF page images  
2. Uses **vLLM or llama.cpp** — pick what is cheaper *and* good enough for Creda JSON judgments  
3. Stays **warm** (request must work immediately — no cold create)  
4. Keeps day-to-day bill inside ~$250 credits when possible  

## Decision (locked — do not reopen unless blocked)
| Workload | Runtime | Why |
|----------|---------|-----|
| **Multimodal (screenshots + PDF pages)** | **vLLM on GPU** (`g4dn.xlarge` via **ECS on EC2**, not Fargate) | ~52% cheaper than g5 in Mumbai; T4 16GB fits Qwen3-VL-4B FP16; llama.cpp VL on CPU too slow |
| **Text-only fallback** | **llama.cpp** Qwen3-4B-Instruct GGUF on existing **Fargate** | Cheap always-on when GPU ASG desired=1 (warm) |

**Default for “Creda works” demos:** GPU vLLM Qwen3 VL warm.  
**Default overnight / low budget:** Fargate text llama (OCR text only for PDFs).

Do **not** try multimodal vLLM on Fargate. Do **not** use SageMaker endpoint for this pass (deleted on purpose).

---

## /architect (short)
1. Confirm GPU quota for `g4dn.xlarge` (prefer over g5 — budget) in ap-south-1  
2. Model id: prefer **Qwen3 / Qwen3.5 4B VL Instruct** (same family as JumpStart `huggingface-vlm-qwen3-5-4b`)  
3. Wire: worker `JUDGE_BACKEND=vllm` → `http://127.0.0.1:8000/v1/chat/completions`  
4. PDF path: poppler/pdftoppm first 1–2 pages → images + optional Textract text in packet  
5. Up/down scripts for GPU ASG (demo day)

Then `/poteto-mode`.

---

## Implement

### 1) GPU ECS service (EC2)
- Capacity provider: ECS-optimized **GPU AMI** + ASG **`g4dn.xlarge`** (desired = 1 (always warm idle)) — **not g5** unless T4 OOMs
- Task: sidecar **vLLM** serving Qwen3 VL + existing **strands-worker**
- Healthcheck vLLM before SQS consume
- Scripts: `scripts/creda_gpu_up.sh` / `creda_gpu_down.sh` (desired 1 ↔ 0)

### 2) Worker
- `JUDGE_BACKEND=vllm` when GPU service up; else `llama`
- Reuse `media_loader.load_case_images` + chat content like `vlm_inference.py`
- Max 2 images; downscale long edge (~1024) for cheap tokens / VRAM
- **Short JSON out**: verdict, headline, reasoning (≤~120 tokens), nextActions[{label,detail,tone}] — keep completions small = cheaper + faster
- Qwen is judge centerpiece; tools (ATS searcher, domain, fees) feed the packet — don’t override verdict with a second rule stamp for the product path

### 3) Cheap tokens knobs (required)
- `max_tokens` ≤ 180–220 for judge JSON  
- temperature 0  
- No long chain-of-thought / disable thinking if model supports it  
- Compact evidence packet (truncate excerpts)  
- Prefer **4B VL** over 7B+/72B  

### 4) Amplify UI (minimum for multimodal)
- + attach PDF + screenshots; show thumbs while waiting  
- Wait copy: “Qwen reading your pages…” when attachments present  
- Fix nextActions string→object so orders aren’t “Next step”

### 5) Acceptance
- [ ] `creda_gpu_up.sh` → vLLM health OK → smoke VL completion with 1 PNG  
- [ ] Live case + screenshot → READY, `agentSource` shows vllm/creda-vlm  
- [ ] Live case + PDF → pages or OCR reach model; coherent ruling  
- [ ] `creda_gpu_down.sh` → GPU stopped; Fargate text path still judges text-only cases  
- [ ] Document $/hr when GPU up  

## Hard fail
- Multimodal claimed on Fargate CPU llama only  
- SageMaker endpoint recreated “for convenience” without up/down discipline  
- Giant max_tokens / verbose CoT burning time and money  

## Done
Architect note · GPU up smoke · one PDF + one screenshot case · GPU down · Amplify note · Ready for Grok test loop

---

## GPU pick (locked for credits ~$238 left of $250)

| Instance | GPU | Mumbai OD | Full month | Hours left @ ~$238 |
|----------|-----|-----------|------------|--------------------|
| ~~g5.xlarge~~ | A10G 24GB | $1.208/hr | ~$882 | ~197h (~8 days) |
| **g4dn.xlarge (USE THIS)** | T4 16GB | **$0.579/hr** | ~$423 | **~410h (~17 days)** |
| g6.xlarge | L4 24GB | $0.966/hr | ~$705 | ~246h |
| Spot either | — | cheap | — | **reject for live judging** (reclaim risk) |

**Still not a full always-on month** on $250. Run pattern:
1. Fargate llama.cpp text Qwen **always warm** (cheap)
2. `creda_gpu_up.sh` → g4dn desired=1 only on demo/judging days
3. `creda_gpu_down.sh` when done

vLLM knobs for T4 16GB: `Qwen/Qwen3-VL-4B-Instruct`, `--dtype float16` (not FP8 — T4 weak FP8), `--max-model-len` 8192–16384, `--gpu-memory-utilization 0.85`, max 2 images, long-edge ≤1024.
