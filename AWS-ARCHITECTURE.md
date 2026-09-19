# Creda AWS Architecture — How We've Configured It

**Purpose:** Living reference document for the Creda WorkOffer Shield MVP on AWS.  
**Last updated:** 17 September 2026  
**Account:** 966499105769 (Curiosity Unlocked) · Region: ap-southeast-2 (Sydney) · Plan: Free

---

## Console access

- URL: `https://966499105769-25bspnlo.ap-southeast-2.console.aws.amazon.com/console/home?region=ap-southeast-2`
- Sign-in: GitHub through the new AWS experience
- CLI profile: `creda-dev` (temporary credentials, valid 12 hours, renewable 90 days)
- Never create root access keys

---

## Architecture at a glance

```
Internet / Creda Frontend
         │
         ▼
┌─────────────────────┐
│  API Gateway        │  HTTP API, $default stage
│  (HttpApi)          │  Throttle: 2 req/s, burst 5
│                     │  CORS: all origins (tighten for prod)
└──────────┬──────────┘
           │  invoke
           ▼
┌─────────────────────┐         ┌──────────────────────────┐
│  API Lambda         │─────────▶  DynamoDB (CasesTable)   │
│  creda-dev-api      │  PutItem │  On-demand, TTL 7 days   │
│  Python 3.12 arm64  │  GetItem │  SSE encrypted           │
│  256MB / 15s        │         └──────────────────────────┘
└──────────┬──────────┘
           │ SendMessage {caseId}
           ▼
┌─────────────────────┐         ┌──────────────────────────┐
│  SQS Worker Queue   │─────────▶  Worker Lambda            │
│  180s visibility    │  trigger │  creda-dev-worker        │
│  4-day retention    │          │  Python 3.12 arm64       │
│  20s long poll      │          │  256MB / 30s             │
└──────────┬──────────┘          └────────────┬─────────────┘
           │ after 3 fails                    │ UpdateItem (COMPLETED)
           ▼                                  ▼
┌─────────────────────┐         ┌──────────────────────────┐
│  Dead-Letter Queue  │         │  DynamoDB (CasesTable)   │
│  14-day retention   │         │  verdict, evidence, TTL  │
└──────────┬──────────┘         └──────────────────────────┘
           │ ≥1 message
           ▼
┌─────────────────────┐
│  CloudWatch Alarm   │  DeadLetterAlarm — triggers on DLQ message count ≥ 1
└─────────────────────┘
                          ┌──────────────────────────┐
                          │  S3 EvidenceBucket       │  Private, SSE-S3, 7-day expiry
                          │  (reserved for future)   │  Not yet used by worker
                          └──────────────────────────┘
                          ┌──────────────────────────┐
                          │  CloudWatch Log Groups   │  7-day retention each
                          │  /aws/lambda/creda-dev-api│
                          │  /aws/lambda/creda-dev-worker│
                          └──────────────────────────┘
```

---

## Service-by-service configuration

### API Gateway HTTP API (`HttpApi`)

| Setting | Value | Why |
|---|---|---|
| Type | HTTP API (v2) | Cheaper and lower-latency than REST API for simple routes |
| Stage | `$default` | Single stage = simpler URLs |
| Routes | GET /health, POST /cases, GET /cases/{caseId} | Minimal public surface |
| Auth | None at gateway level | App-layer token auth via X-Case-Token header |
| Throttle | 2 req/s rate, burst 5 | Basic abuse guard on Free Plan |
| CORS | AllowOrigins: `*`, AllowHeaders: content-type + x-case-token | Open for dev; tighten to frontend URL for prod |
| Access logs | JSON to CloudWatch | requestId + status + route only; no body |

**How we use it:** API Gateway is purely a router. It forwards all three routes to the API Lambda. No JWT, no Cognito — the per-case token is validated in Python code using `hmac.compare_digest`.

---

### Lambda — API function (`creda-dev-api`)

| Setting | Value | Why |
|---|---|---|
| Runtime | Python 3.12 arm64 | Best price/performance for Python on Lambda |
| Memory | 256 MB | Comfortable for boto3 + checks + tldextract |
| Timeout | 15s | API Gateway HTTP API max is 29s; 15s is sufficient |
| Concurrency | No reservation | Free Plan has 10 total; no reservation needed |
| Environment | TABLE_NAME, QUEUE_URL, ENABLE_BEDROCK, BEDROCK_MODEL_ID | Injected from CloudFormation |
| IAM role | `ApiRole` | PutItem + GetItem on CasesTable; SendMessage on WorkerQueue; logs only |

**What it does:**
1. `GET /health` → returns `{"status": "ok"}` immediately
2. `POST /cases` → validates input, generates UUID + token, stores `SHA-256(token)` in DynamoDB, sends `{caseId}` to SQS, returns 202 with caseId + raw token
3. `GET /cases/{caseId}` → looks up by caseId, verifies token via constant-time compare, returns case fields

**Key security decisions:**
- Raw token never stored — only SHA-256 hexdigest
- `hmac.compare_digest` prevents timing attacks on token comparison
- 404 returned for both "not found" and "bad token" to avoid oracle attacks
- Body size capped at 64 KB, text at 30,000 chars

---

### Lambda — Worker function (`creda-dev-worker`)

| Setting | Value | Why |
|---|---|---|
| Runtime | Python 3.12 arm64 | Same image as API |
| Memory | 256 MB | Enough for tldextract + rapidfuzz + boto3 |
| Timeout | 30s | SQS visibility is 180s; retries before DLQ |
| Batch size | 1 | One case per invocation = clear blast radius |
| Response type | ReportBatchItemFailures | Partial batch failure — bad messages go to DLQ without blocking good ones |
| Max concurrency | 2 (SQS ScalingConfig) | Free Plan limit is 10 total; leave headroom |
| IAM role | `WorkerRole` | GetItem + UpdateItem on CasesTable; ReceiveMessage + DeleteMessage on WorkerQueue; logs |

**What it does:**
1. Reads `caseId` from SQS message body
2. Loads the case from DynamoDB
3. Runs `extract_claims()` (finds payment demands etc. via regex)
4. Runs `sender_evidence()` (checks sender email domain)
5. Runs `compute_verdict()` (deterministic policy — model cannot override)
6. Updates DynamoDB with COMPLETED status + verdict fields using conditional expression (`#s = :queued`) to prevent duplicate overwrites

**Idempotency:** The conditional update `status = QUEUED` means a second delivery of the same message silently no-ops — `ConditionalCheckFailedException` is caught and swallowed.

---

### DynamoDB (`creda-dev-CasesTable-*`)

| Setting | Value | Why |
|---|---|---|
| Billing | PAY_PER_REQUEST | Zero charge when idle — critical for Free Plan |
| Key | `caseId` (hash) | UUID, globally unique per case |
| TTL | `expiresAt` = createdAt + 7 days | Auto-deletes expired cases; API rejects them early |
| Encryption | SSE (AWS managed) | No charge, no customer-managed key overhead |
| DeletionPolicy | Retain | Stack deletion doesn't wipe data |

**What we store per case:**

```
caseId          UUID
tokenHash       SHA-256(accessToken)
offerText       Input text (stored for worker; not logged)
senderEmail     Input email
links           Input links list
employerHint    Input employer name
locale          Input locale
status          QUEUED → COMPLETED (or FAILED)
stage           queued → complete
verdict         high_risk / unverified / no_conflict_found
headline        Human-readable summary
claims          [{id, type, value, quote}]
evidence        [{id, tier, check, outcome, excerpt}]
unresolved      [string]
nextActions     [string]
patternVersion  "2026-09-17"
createdAt       Unix epoch
processedAt     Unix epoch
expiresAt       Unix epoch (TTL)
```

**Consistent reads:** Worker writes `status=COMPLETED`; API uses `ConsistentRead=True` on GET to avoid reading stale QUEUED status from eventually-consistent read.

---

### SQS — Worker Queue (`creda-dev-WorkerQueue-*`)

| Setting | Value | Why |
|---|---|---|
| Visibility timeout | 180s | 6× worker timeout (30s) — standard AWS recommendation |
| Message retention | 4 days | Long enough to retry transient failures |
| Long polling | 20s | Reduces empty-receive API calls (cost) |
| Encryption | SQS managed SSE | No cost, no CMK overhead |
| DLQ | After 3 receives | 3 attempts before declaring a message unprocessable |

**Message format:** `{"caseId": "<uuid>"}` — no offer text, no tokens, no PII in queue.

---

### SQS — Dead-Letter Queue (`creda-dev-DeadLetterQueue-*`)

| Setting | Value | Why |
|---|---|---|
| Retention | 14 days | Time to investigate + redrive |
| Alarm | CloudWatch metric alarm → fires when ≥ 1 message visible | Early warning of worker bugs |

If DLQ fires: check `/aws/lambda/creda-dev-worker` logs, fix the code, redeploy, then redrive the DLQ manually.

---

### S3 — Evidence Bucket (`creda-dev-evidencebucket-*`)

| Setting | Value | Why |
|---|---|---|
| Access | Fully private (all block-public settings enabled) | No public evidence |
| Ownership | BucketOwnerEnforced (ACLs disabled) | Modern S3 best practice |
| Encryption | SSE-S3 (AES256) | No cost |
| Lifecycle | Objects expire after 7 days | Matches case TTL |
| CORS | None configured | Not accessed from browser yet |

Currently unused by the worker — reserved for when file/screenshot evidence is re-added.

---

### CloudWatch

| Resource | Purpose |
|---|---|
| `/aws/lambda/creda-dev-api` | API function logs, 7-day retention |
| `/aws/lambda/creda-dev-worker` | Worker function logs, 7-day retention |
| Access log group | API Gateway access logs (requestId, status, route), 7-day |
| DeadLetterAlarm | Metric alarm: DLQ messages ≥ 1, 5-min period, no SNS action (check console) |

**Logging policy:** Offer text, email addresses, URLs, tokens, and SQS message bodies must never appear in log records.

---

### IAM Roles

**ApiRole** — API Lambda only:
- `dynamodb:PutItem` + `dynamodb:GetItem` on CasesTable ARN
- `sqs:SendMessage` on WorkerQueue ARN
- `logs:CreateLogStream` + `logs:PutLogEvents` on ApiLogs ARN

**WorkerRole** — Worker Lambda only:
- `dynamodb:GetItem` + `dynamodb:UpdateItem` on CasesTable ARN
- `sqs:ReceiveMessage` + `sqs:DeleteMessage` + `sqs:GetQueueAttributes` on WorkerQueue ARN
- `logs:CreateLogStream` + `logs:PutLogEvents` on WorkerLogs ARN
- `bedrock:InvokeModel` + `bedrock:InvokeModelWithResponseStream` — conditional on `EnableBedrock=true` (currently false)

---

## Bedrock / Strands configuration (disabled)

The Strands agent scaffold (`src/agent_workflow.py`) is wired but not called. `EnableBedrock=false` is the CloudFormation parameter. The default model is `amazon.nova-micro-v1:0` (available in ap-southeast-2).

**To enable Bedrock:**
1. Add evaluation fixtures in `tests/` for real, scam, and ambiguous offers
2. Confirm model ID and current price in Sydney console → Bedrock → Model catalog
3. Add per-case model-call ceiling env var (`MAX_MODEL_CALLS_PER_CASE`)
4. Deploy: `python scripts/deploy.py ... --enable-bedrock`
5. Run `python scripts/smoke.py` and check Billing → Credits Usage immediately

**Hard rule:** `compute_verdict()` in `src/verdict.py` is the sole authority. Model output populates `claims` explanation and `verdictCandidate` field only — it cannot override the final verdict.

---

## Cost footprint (Free Plan)

No EC2, no RDS, no NAT gateway, no VPC, no provisioned concurrency, no customer-managed KMS, no SageMaker, no Step Functions, no OpenSearch.

Metered at idle:
- DynamoDB: $0 (PAY_PER_REQUEST, no reads/writes when idle)
- Lambda: $0 (no invocations when idle)
- SQS: minimal polling cost (~$0.004/million requests)
- S3: negligible storage for SAM artifacts
- CloudWatch: log storage after 7 days expires

Do not upgrade to Paid Plan. Preserve credits for judge demos.

---

## Agent Toolkit integration

Kiro is connected to this AWS account via the Agent Toolkit MCP server:

- Skills: 23 AWS skills installed at `~/.kiro/skills/`
- MCP config: `~/.kiro/settings/mcp.json` → `aws-mcp` entry
  - Profile: `creda-dev`
  - Region metadata: `ap-southeast-2`
  - Service endpoint: `us-east-1` (Agent Toolkit requirement)

The MCP server gives Kiro read access to AWS documentation and service guidance. It does not have write access to your AWS account — all infrastructure changes go through `deploy.py` + SAM/CloudFormation.

---

## Reproduce everything from scratch

```bash
# 1. Authenticate
aws login --profile creda-dev --region ap-southeast-2

# 2. Verify
aws sts get-caller-identity --profile creda-dev --region ap-southeast-2

# 3. Deploy
cd /Users/siva/Documents/Codex/2026-09-17/creda-aws-backend/outputs/creda-backend
export PATH="$(cd ../../work/bin && pwd):$(cd ../../work/venv/bin && pwd):$PATH"
python scripts/deploy.py --profile creda-dev --account 966499105769 --region ap-southeast-2 --stack creda-dev

# 4. Smoke test
python scripts/smoke.py --profile creda-dev --region ap-southeast-2 --stack creda-dev
```
