# Creda Eraser.io architecture diagram prompt — CURRENT MVP only

**Copy everything below the line into Eraser.io (AI / diagram prompt).**  
Do **not** draw SageMaker, g4dn/vLLM, Bedrock, Cognito, Step Functions, or open-web search — those are not live production today.

---

## Eraser prompt (copy-paste)

```
Draw a clean system architecture diagram for Creda WorkOffer Shield CURRENT live MVP (2026-09-19). Region ap-south-1 (Mumbai). Title: "Creda WorkOffer Shield — Live MVP".

STYLE
- Grouped boxes with clear labels; solid arrows for request/data flow; dashed arrows for async queues/schedules.
- No future/aspirational components. No SageMaker. No g4dn GPU. No Cognito. No Step Functions.
- Annotate short notes on edges where helpful.

GROUPS / REGIONS

1) Clients
   - Node "Amplify UI" — static site main.d32sg54oqu2gcb.amplifyapp.com (HTML/CSS/app.js). Label: poll 1.5s, ruling board.
   - Node "Telegram @CredashieldBot" — optional channel. Label: PARTIAL — webhook auth required.
   - Node "Browser upload" — optional screenshots/PDF via presigned PUT.

2) Edge / API
   - Node "API Gateway HTTP API" — api id host x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com
     Routes label: GET /health · POST /cases · GET /cases/{id} · POST /cases/{id}/followup · POST /upload-url · POST /reports/scam · POST /telegram/webhook

3) Intake & storage (stack creda-mumbai)
   - Node "Intake Lambda" — create case, token (X-Case-Token), upload-url, reports, telegram webhook.
   - Node "DynamoDB Cases" — case state, evidence, agent stream/verdict, reports.
   - Node "S3 EvidenceBucket" — cases/uploads/* + curated bundle creda-demo-2026-09-17.

4) Evidence gather (tools → packet, not final stamp)
   - Node "SQS WorkerQueue" (+ DLQ implied).
   - Node "Gatherer / Worker Lambda" — deterministic checks + SEARCHER.
   - Node "Searcher / ATS" — 17 ATS sources, 47 employers indexed; openWebPerRequest=false; live board or 667-vacancy cache; pipeline logs "Searching official ATS…".
   - Node "Forum / advisory index" — T3 discovery exhibits ev_forum_* (not sole verdict).

5) Judge (live)
   - Node "SQS QwenQueue" — agentQueueConfigured=true.
   - Node "ECS Fargate cluster creda-qwen-cpu" — service DesiredCount=1 WARM IDLE (not scale-to-zero).
   - Node "llama.cpp Qwen3-4B-Instruct GGUF" — text judge; streams agentStreamText; agentSource=creda; agentStatus READY.
   - Small note: "GPU g4dn + vLLM Qwen3-VL NOT DEPLOYED — omit from diagram".

6) Schedules
   - Node "EventBridge schedule CredaDailyIngest" — daily allowlisted refresh (policies, Greenhouse Stripe, advisories).
   - Node "Ingest / evidence-refresh Lambda" — updates S3/index; health lastForumIngest + lastAtsRefresh.

EDGES (labeled)

Amplify UI -->|POST /cases| API Gateway
Amplify UI -->|GET /cases poll stream fields| API Gateway
Amplify UI -->|POST /followup| API Gateway
Amplify UI -->|POST /upload-url| API Gateway
Amplify UI -->|POST /reports/scam| API Gateway
Browser upload -->|PUT presigned| S3 EvidenceBucket
Telegram -->|POST /telegram/webhook| API Gateway

API Gateway --> Intake Lambda
Intake Lambda --> DynamoDB Cases
Intake Lambda --> SQS WorkerQueue
Intake Lambda -->|presign| S3 EvidenceBucket

SQS WorkerQueue --> Gatherer / Worker Lambda
Gatherer / Worker Lambda --> Searcher / ATS
Gatherer / Worker Lambda --> Forum / advisory index
Gatherer / Worker Lambda --> DynamoDB Cases
Gatherer / Worker Lambda --> SQS QwenQueue
Gatherer / Worker Lambda -->|read curated| S3 EvidenceBucket

SQS QwenQueue --> ECS Fargate cluster creda-qwen-cpu
ECS Fargate cluster creda-qwen-cpu --> llama.cpp Qwen3-4B-Instruct GGUF
llama.cpp Qwen3-4B-Instruct GGUF -->|verdict + agentPresentation + stream| DynamoDB Cases
DynamoDB Cases -.->|poll reads| Amplify UI

EventBridge schedule CredaDailyIngest --> Ingest / evidence-refresh Lambda
Ingest / evidence-refresh Lambda --> S3 EvidenceBucket
Ingest / evidence-refresh Lambda --> Forum / advisory index

ONE-SHOT CHECK FLOW CALLOUT (small sequence annotation or sidebar)
User paste → API → Gatherer tools (searcher, policies, forums) → evidence packet → Qwen/llama stream → Amplify ruling board.
Follow-up restarts gather+judge (PARTIAL UX: ruling can reset).

LEGEND
- Solid: sync HTTP / Lambda invoke
- Dashed: SQS async or EventBridge schedule
- Searcher feeds packet only; model writes stamp (agentSource=creda)
```

---

## Suggested diagram nodes (8–12 for a compact version)

If Eraser needs a minimal set, use exactly these **11 nodes**:

1. Amplify UI  
2. Telegram bot (partial)  
3. API Gateway (Mumbai)  
4. Intake Lambda  
5. DynamoDB Cases  
6. S3 Evidence + uploads  
7. Gatherer Lambda + Searcher/ATS  
8. SQS QwenQueue  
9. ECS Fargate Qwen (llama.cpp)  
10. EventBridge daily ingest  
11. Ingest / refresh Lambda  

---

## MVP polish status (label on diagram footer)

**Solid today**
- End-to-end Check: create → gather (ATS searcher + policies + forum exhibits) → Fargate llama judge → Amplify board  
- Multimodal upload URL + S3  
- Report-a-scam API  
- EventBridge/daily refresh reflected in `/health`  
- Case token auth (no Cognito)

**Half-wired / gaps**
- g4dn multimodal judge **not live** (templates only)  
- Telegram webhook **auth-gated / ops setup**  
- Follow-up works but can **clobber headline** and omit assistant turn  
- Searcher is **index/ATS**, not open web; often no `ev_search_*` exhibit id  
- Deployed Lambda source **outside** this git tree (`creda-aws-backend`)  
- nextActions / UI object shape sometimes mismatched  

**Explicitly out of CURRENT diagram:** SageMaker endpoint, Bedrock, Cognito, Step Functions, GPU ASG, open-web crawler.


## Lock (2026-09-19)
**NO multimodal live.** Text-only judge path. Screenshot/PDF/VLM = not ready until g4dn/vLLM ships.
