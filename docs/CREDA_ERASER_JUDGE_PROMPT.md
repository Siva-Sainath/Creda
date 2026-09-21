# Creda — Eraser prompt (hackathon-judge style)

## What winners do (research summary)

1. **15-second rule** — judge grasps flow without reading a novel (SIH playbooks).
2. **One request path** first — user → edge → services → data → model → result (not every queue/DLQ).
3. **Layers / clusters**, not 20 free-floating boxes (Eraser guidance: 3–5 sentence prompt + groups).
4. **Official cloud icons** + short edge labels (1–2 words). No route laundry lists.
5. **One deliberate trade-off** called out (ours: warm g4dn for multimodal vs CPU-only).
6. **Refine in Eraser** with tiny follow-ups: “more spacing”, “use AWS icons”, “hide DLQ”.

Tool order for quality: **Eraser (best icons/layout)** → draw.io AWS icons → python `diagrams` → custom PNG last.

---

## Paste into Eraser (cloud architecture)

```
Create a clean AWS cloud architecture diagram for Creda WorkOffer Shield (hackathon judge slide). Region ap-south-1.

GOAL: readable in 15 seconds. Left-to-right. Official AWS icons. Soft cluster boxes. Short arrow labels (1–2 words). No route lists, no DLQs, no Cognito, no SageMaker.

STORY (one path):
Job seeker pastes a suspicious job offer on Amplify web UI or Telegram → API Gateway → Intake Lambda creates a case in DynamoDB and stores uploads in S3 → Worker Lambda + Searcher gather employer/ATS/policy evidence into a packet → SQS → LLM as judge on g4dn (vLLM Qwen-VL, multimodal) writes the stamp → UI polls DynamoDB and shows Ruling + Why-scam tiles.

CLUSTERS:
1. Clients — Amplify, Telegram
2. Edge — API Gateway
3. Case — Intake Lambda, DynamoDB, S3
4. Evidence — Gatherer/Searcher Lambda, EventBridge daily refresh (dashed)
5. LLM as judge — SQS, EC2/ECS g4dn + vLLM Qwen-VL

FOOTER CHIP: “Tools find evidence · Qwen stamps the ruling · Warm GPU for screenshots”

Layout: generous spacing, no crossing arrows, title “Creda WorkOffer Shield”.
```

### Eraser refine follow-ups (send one at a time)

1. `Use official AWS icons for every AWS service and a Telegram icon for the bot`
2. `Increase horizontal spacing; straighten arrows; remove clutter labels`
3. `Make the LLM as judge cluster visually emphasized (slightly larger)`
4. `Export PNG at high resolution for slides`
