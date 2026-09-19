# AWS data handoff for Creda

**Audience.** An agent or engineer who owns the deployed AWS stack (SAM, S3, Lambda, DynamoDB, Bedrock, Amplify).

**Goal.** Wire the backend to Creda datasets without running heavy ETL in Lambda. Judges must get a verdict from a public URL even when Bedrock is slow or unavailable.

**Repo root.** `/Users/siva/Documents/first_commit_hack`

---

## What each side owns

| Owner | Responsibility |
|---|---|
| **This repo (data foundation)** | Fetch sources, run ETL, validate schema, build the deploy bundle, document tiers and product rules |
| **AWS backend agent** | Deploy SAM stack, upload bundle to S3, set env vars, connect Amplify frontend, verify `/health` and three demo cases |

The judge-critical path does **not** depend on Glue, Athena, or a live full ETL run. Glue is optional for audits later. See `data/reports/aws_ingestion_manifest.md`.

---

## Architecture (judge path)

```
Local laptop                         AWS (after deploy)
─────────────────                    ──────────────────
run_etl.py                           Intake Lambda  POST /cases
  └─ data/curated/* (37k rows)         └─ SQS
build_deploy_bundle.py                     Worker Lambda
  └─ deploy/bundle/ (~192 KB)                ├─ read curated/* from S3
upload_deploy_bundle.py                      ├─ deterministic checks (always)
  └─ s3://BUCKET/curated/*                   └─ Strands + Bedrock (optional headline)
                                             Ingest Lambda (daily, lightweight raw refresh)
Amplify frontend  ──HTTP──►  API Gateway
```

**Principle applied.** Deterministic checks run before any model call. Bedrock only writes the headline explanation. Verdict logic lives in `backend/worker/deterministic.py`.

---

## Evidence tiers and product rules

These rules are fixed. Do not change them without updating ETL and worker together.

| Tier | Meaning | Can alone produce `confirmed_scam`? | Runtime use |
|---|---|---|---|
| **T1** | Official employer policy, official vacancy, government advisory | Yes, when matched as a **conflict** with user paste | Deploy bundle + worker |
| **T2** | Derived signals (free mailbox, domain mismatch) | No | Worker only |
| **T3** | Historical datasets, synthetic, Gmail private, message-level duplicates | No | Local eval and research only. **Not in deploy bundle.** |

**Verdict values from worker:** `high_risk`, `no_conflict_found`, `unverified`, or incomplete if no verdict.

**Regenerate tier counts:**

```bash
cd /Users/siva/Documents/first_commit_hack
.venv/bin/python -c "
import json
from collections import Counter
recs=[json.loads(l) for l in open('data/curated/evidence.jsonl') if l.strip()]
print('by tier:', dict(Counter(r['evidence_tier'] for r in recs)))
print('by record_type:', dict(Counter(r['record_type'] for r in recs)))
"
```

At commit time (2026-09-17): **37,525** evidence rows. **T1: 2,336**. **T3: 35,189**.

---

## Local pipeline (build once on laptop)

| Step | Command | Output |
|---|---|---|
| 1. Fetch sources | `python scripts/fetch_sources.py` | `data/raw/<source_id>/<date>/` |
| 2. Full ETL | `python scripts/run_etl.py` | `data/curated/*`, `data/reports/*` |
| 3. Deploy bundle | `python scripts/build_deploy_bundle.py` | `deploy/bundle/*` |
| 4. Upload (after SAM) | `python scripts/upload_deploy_bundle.py --bucket BUCKET` | `s3://BUCKET/curated/*` |

**Core library:** `scripts/creda/core.py` (normalize, PII redact, claims, dedupe), `scripts/creda/pipeline.py` (ingest all sources, write curated files).

**Schema:** `schemas/evidence.schema.json`, `schemas/glue_evidence_table.json`

**Source registry:** `data/source_registry.yaml` (not every downloaded folder is listed yet; see fetch report below).

---

## Deploy bundle (what AWS reads at runtime)

Built by `scripts/build_deploy_bundle.py`. Uploaded to **`s3://{DataBucket}/curated/`**.

| File | Rows / items | Purpose in worker |
|---|---|---|
| `manifest.json` | 1 | Health gate. Intake checks `curated/manifest.json` exists |
| `employer_policies.jsonl` | 6 | Match employer hint. Fee policy conflict. Official domains |
| `vacancy_index.jsonl` | 500 (cap) | Strands context for official roles. Not used in deterministic verdict today |
| `channel_patterns.jsonl` | 22 | WhatsApp / Telegram scam signals from gov advisories |
| `recruiting_process_patterns.jsonl` | 6 | Legitimate process patterns from T1 policies |
| `employer_aliases.json` | 10 keys | Alias lookup (Amazon, Google, KPMG, etc.) |
| `demo_cases.json` | 3 | Frontend one-click demos. Expected verdicts baked in |

**Bundle counts** (regenerate: `python scripts/build_deploy_bundle.py`):

```json
{
  "employer_policies": 6,
  "vacancies": 500,
  "channel_patterns": 22,
  "recruiting_process_patterns": 6,
  "demo_cases": 3
}
```

**Slimming rules.** Policies truncated to 2,500 char excerpt. Vacancies are T1 `official_vacancy` rows only, max 500. Full `evidence.jsonl` is **not** uploaded to the judge path.

**Upload also writes:** `s3://BUCKET/manifests/{date}/ingestion.json` (audit copy of bundle manifest).

---

## Full curated datasets (local only unless noted)

| Dataset | Path | Lines | Used at runtime? | Role |
|---|---|---:|---|---|
| Canonical evidence | `data/curated/evidence.jsonl` | 37,525 | No (full file) | Master table. Feeds bundle builder and parquet |
| Evidence parquet | `data/curated/evidence.parquet` | 37,525 rows | No (judge path) | Glue / Bedrock KB / Athena (post-MVP) |
| Employer policies | `data/curated/employer_policies.jsonl` | 6 | **Yes** (slim copy in bundle) | T1 no-fee statements, official domains |
| Official vacancies | subset of evidence | 2,314 in full ETL | **Yes** (500 in bundle) | Role and URL cross-check context |
| Channel patterns | `data/curated/channel_patterns.jsonl` | 22 | **Yes** | Scam channel tactics from gov sources |
| Recruiting process patterns | `data/curated/recruiting_process_patterns.jsonl` | 6 | **Yes** | Legitimate hiring flow patterns |
| Government patterns | `data/curated/patterns.jsonl` | 12 | No | Advisory summaries for research / future KB |
| Evaluation cases | `data/curated/evaluation_cases.jsonl` | 50 | No | Offline eval design. 2,350 eval-eligible records in reports |
| CAFC aggregate | `data/curated/cafc_aggregate.jsonl` | 39 | No | UK fraud category baseline |
| Source snapshot | `data/curated/source_snapshots/2026-09-17.jsonl` | 1 | No | Provenance metadata for ingestion audit |
| Gmail private | `data/private/gmail_recruitment_candidates.jsonl` | small | **No** | T3. Never upload to public bucket |
| Raw sources | `data/raw/<source_id>/` | ~32 folders | Partial | Daily ingest refreshes 6 URLs only |

---

## Raw sources downloaded (2026-09-17)

Full list from `data/reports/fetch_report.json` and `data/raw/`.

### T1 runtime-relevant (policies and vacancies)

| source_id | Type | In deploy bundle? |
|---|---|---|
| `amazon_recruitment_fraud_policy` | Employer policy | Yes (slim) |
| `google_recruitment_fraud_policy` | Employer policy | Yes |
| `kpmg_recruitment_fraud_policy` | Employer policy | Yes |
| `amex_recruitment_fraud_policy` | Employer policy | Yes |
| `valero_recruitment_scams_2025` | Employer policy | Yes |
| `wipro_recruitment_fraud_policy` | Employer policy | Yes |
| `greenhouse_stripe_jobs` | Official vacancy API | Yes (in vacancy index) |
| `greenhouse_airbnb_jobs` | Official vacancy API | Yes |
| `greenhouse_discord_jobs` | Official vacancy API | Yes |
| `greenhouse_figma_jobs` | Official vacancy API | Yes |
| `greenhouse_databricks_jobs` | Official vacancy API | Yes |
| `lever_spotify_jobs` | Official vacancy API | Yes |
| `ashby_notion_jobs` | Official vacancy API | Yes |

### T1 government and guidance (channel / pattern inputs)

| source_id | Role in ETL |
|---|---|
| `i4c_captcha_advisory_2025` | Channel patterns |
| `i4c_fake_job_sms_advisory` | Channel patterns |
| `i4c_handbook_2025` | Channel patterns |
| `cyberdost_job_fraud_tips` | Channel patterns |
| `nasc_job_scam_fusion_report_2025` | Channel patterns |
| `mea_yangon_overseas_job_scam_2024` | Channel patterns |
| `scamwatch_au_job_scams` | Channel patterns |
| `ca_ag_job_scam_alert_2025` | Channel patterns |
| `ic3_annual_report_2024` | Evidence / patterns |
| `ncsc_phishing_guidance` | Evidence |
| `i4c_cybercrime_portal` | Registry / evidence |
| `mea_overseas_employment` | Registry / evidence |
| `emigrate_portal` | Registry / evidence |
| `cafc_fraud_reports` | CAFC aggregate |

### T3 research and baseline only (not in deploy bundle)

| source_id | Notes |
|---|---|
| `emscad` | Historical 2012–2014 baseline. Immutable |
| `difraud_job_scams` | HF job_scams splits |
| `kaggle_fake_vs_real_synthetic` | Synthetic. Pattern exploration only |
| `kaggle_fake_job_postings_srisai` | Quarantined. License review pending |
| `gmail` (private) | T3 offer messages. No public upload |

### Blocked or failed fetch

| source_id | Status |
|---|---|
| `ftc_job_scams` | 403 |
| `scambench_employment` | Hugging Face 401 (needs auth) |
| `greenhouse_shopify_jobs` | 404 (board removed) |
| Infosys / TCS policies | 403 on probe |
| NetApp policy | 403 |

---

## How the worker uses each bundle file

**Entry:** `backend/worker/handler.py`

1. Load policies and channels from S3 via `shared/s3_data.py` (cached in `agent.py`).
2. `deterministic.run_deterministic_checks()`:
   - Free mailbox domains (`gmail.com`, `outlook.com`, etc.)
   - Sender domain vs policy `official_domains`
   - Fee language vs policy `no_fee_statement`
   - WhatsApp / Telegram vs `channel_patterns.jsonl`
3. `compute_verdict()` maps evidence to `high_risk`, `no_conflict_found`, or `unverified`.
4. `strands_explain()` adds headline via Bedrock. Falls back to template if Strands fails.

**Set `DISABLE_STRANDS=true`** on WorkerFunction to test deterministic-only path.

**Intake health:** `backend/intake/app.py` → `HEAD curated/manifest.json`.

**Daily ingest:** `backend/ingest/handler.py` fetches 6 URLs into `raw/` prefix. It does **not** rebuild the curated bundle. Re-run local ETL + bundle upload to refresh judge data.

---

## AWS integration checklist

Complete these in order.

1. **Deploy stack:** `bash scripts/deploy.sh` or `cd infra && sam build && sam deploy --guided`
2. **Upload bundle:** `python scripts/upload_deploy_bundle.py --bucket <DataBucketName>`
3. **Verify health:**
   ```bash
   curl -s "$API_URL/health" | jq .
   # ok: true, dataReady: true
   ```
4. **Run demo cases** from `frontend/index.html` or POST payloads in `deploy/bundle/demo_cases.json`
5. **Amplify:** Connect `frontend/`, set `VITE_API_URL` to stack `ApiUrl` output
6. **Optional Strands layer:** `StrandsLayerArn` parameter in `infra/template.yaml`
7. **Bedrock:** Enable `anthropic.claude-3-5-haiku-20241022-v1:0` (or your `BedrockModelId`) in deploy region

**Stack outputs:** `ApiUrl`, `DataBucketName` (see `infra/template.yaml` Outputs section).

**Env vars (Globals in SAM):** `DATA_BUCKET`, `CASES_TABLE`, `BEDROCK_MODEL_ID`, `PATTERN_VERSION`.

---

## Prior session work summary (data + deploy prep)

Completed locally. AWS deploy was **not** run (no billable resources created yet).

| Area | What was done |
|---|---|
| ETL | Full pipeline through 37,525 evidence rows. 0 schema validation errors |
| Dedupe fix | Fuzzy dedupe scoped to message-level sources only (fixed O(n²) hang) |
| Deploy bundle | `scripts/build_deploy_bundle.py` + `scripts/upload_deploy_bundle.py` |
| Lambdas | Intake, Worker (Strands + deterministic), Ingest (lightweight daily) |
| SAM | `infra/template.yaml` (HttpApi, SQS, DynamoDB, S3, EventBridge) |
| Frontend | `frontend/index.html` with 3 demo buttons + health warning |
| Docs | `DEPLOY.md`, `infra/samconfig.toml.example` |
| Reliability | Removed Step Functions from judge path. Pre-seed S3 before demo |

---

## Files the AWS agent should read first

1. `DEPLOY.md` — judge checklist and failure table
2. `scripts/build_deploy_bundle.py` — what goes to S3
3. `backend/worker/deterministic.py` — verdict logic
4. `backend/shared/s3_data.py` — S3 keys under `curated/`
5. `data/reports/aws_ingestion_manifest.md` — future Glue / KB layout
6. `data/reports/source_quality_ranking.md` — source tier rationale

---

## Open items (non-blocking for demo)

- Sync `data/source_registry.yaml` with all folders in `data/raw/`
- Ingest ScamBench if Hugging Face token available
- Glue crawler and Bedrock KB split documented but not on judge critical path
- Wipro policy is in bundle; demo cases use Amazon, KPMG, Stripe only

---

## Quick verification script

```bash
cd /Users/siva/Documents/first_commit_hack
python scripts/build_deploy_bundle.py
test -f deploy/bundle/manifest.json && echo "bundle ok"
bash scripts/prepare_lambdas.sh
# After deploy + upload:
curl -s "$API_URL/health"
```

**Expected demo verdicts** (from `deploy/bundle/demo_cases.json`):

| demo_id | expected_verdict |
|---|---|
| `amazon-fee-gmail` | `high_risk` |
| `kpmg-fee-training` | `high_risk` |
| `stripe-legitimate-style` | `no_conflict_found` |
