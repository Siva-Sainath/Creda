# Creda data module — Codex handoff

**Repo:** `/Users/siva/Documents/first_commit_hack`  
**Purpose:** Evidence-backed recruitment-offer verification (India + global). Static curated data + deterministic checks + optional Bedrock/Strands headline.  
**Status (2026-09-17):** Local ETL complete. AWS deploy scripts ready. Live web-retrieval pipeline **not yet built** (recommended next phase).

---

## What was achieved

### Data foundation

| Output | Count | Role |
|---|---:|---|
| `data/curated/evidence.jsonl` | 40,041 rows | Master evidence table (research, eval, parquet) |
| `data/curated/employer_policies.jsonl` | 10 | T1 employer fraud/policy pages |
| `data/curated/employer_index.json` | 47 employers | Coverage matrix (tier, region, policy/ATS flags) |
| `data/curated/scam_tactics.jsonl` | 12 | Dynamic scam tactic registry (regex + user guidance) |
| `data/curated/channel_patterns.jsonl` | 26 | Gov-reported channel/tactic patterns |
| `data/curated/recruiting_process_patterns.jsonl` | 10 | Structured employer process profiles |
| `data/curated/evaluation_cases.jsonl` | 47 | Offline eval cases |
| `deploy/bundle/` | ~1 MB | Lambda/S3 runtime bundle (not full ETL) |

### Employer policies ingested (T1)

1. Amazon  
2. Google (manual verified snapshot — live SPA page has no extractable text)  
3. Microsoft (manual verified snapshot)  
4. TCS (Wayback snapshot — live site blocks bots)  
5. Infosys (manual verified snapshot — live site 403)  
6. Wipro  
7. KPMG  
8. American Express  
9. Valero  
10. NetApp (Wayback)

### Employer registry (`data/employer_registry.yaml`)

47 companies across:
- **Big tech:** Amazon, Google, Microsoft, Meta, Apple, Netflix, Adobe, Salesforce, Oracle, IBM, Uber, Flipkart, …
- **India IT:** TCS, Infosys, Wipro, HCL, Cognizant, Tech Mahindra, Accenture, Capgemini, Freshworks, Zoho, Razorpay, …
- **Startups / mid-market with live ATS:** Stripe, Coinbase, Figma, Databricks, Discord, Airbnb, Anthropic, Datadog, MongoDB, Cloudflare, Vercel, Reddit, Twilio, Lyft, Instacart, Spotify (Lever), Notion (Ashby), …

Only **10/47** have downloadable policy text today. The other **37** are registry stubs (domains, careers URLs, aliases) ready for live fetch.

### Live vacancy boards (Greenhouse/Lever/Ashby)

15 Greenhouse boards fetched: stripe, coinbase, figma, databricks, discord, airbnb, anthropic, datadog, mongodb, cloudflare, vercel, reddit, twilio, lyft, instacart. Plus Lever (Spotify), Ashby (Notion). **1,000** vacancies in deploy bundle (cap).

### Government / guidance sources

I4C advisories + handbook 2025, CyberDost, NASC 2025 (AU), IC3 2024, NCSC, MEA/eMigrate, CA AG 2025, Scamwatch AU, FTC job scams (browser UA fetch), LinkedIn job scam help page.

### Historical / eval-only (T3 — never standalone verdict)

EMSCAD, DiFrauD, Kaggle synthetic, Gmail private samples. ScamBench blocked (HF 401 without token).

### Runtime application stack (built, deploy optional)

| Component | Path | Role |
|---|---|---|
| ETL pipeline | `scripts/creda/pipeline.py` | Ingest → curated JSONL/parquet |
| Deploy bundle | `scripts/build_deploy_bundle.py` | Slim S3 bundle for Lambda |
| Intake API | `backend/intake/app.py` | POST /cases, GET /health, /coverage, /tactics |
| Worker | `backend/worker/handler.py` | Deterministic checks → Strands/Bedrock headline |
| Ingest Lambda | `backend/ingest/handler.py` | Daily lightweight raw refresh (6 URLs) |
| Frontend | `frontend/index.html` | Paste offer + demo buttons |
| SAM | `infra/template.yaml` | API Gateway, SQS, DynamoDB, S3, EventBridge |

### Verification behavior (product rules)

- **T1** official policy/gov source can drive **high_risk** when offer **conflicts** (e.g. fee vs no-fee policy).
- **T2** signals (free mailbox, wrong domain) support verdict but cannot alone confirm scam.
- **T3** historical/synthetic/Gmail cannot produce confirmed scam alone → **unverified** if no T1.
- Worker runs **deterministic checks first**; Bedrock only adds headline. Set `DISABLE_STRANDS=true` on worker for deterministic-only demos.

### What the data enables today

- Flag obvious scams for **10 named employers** with cited policy excerpts.
- Flag **12 generic scam tactics** (fee, WhatsApp interview, CAPTCHA task, crypto/gift card, fake check, etc.) with user-facing guidance.
- Cross-check **1,000 official vacancies** (role existence — loaded in bundle, not yet wired to verdict logic).
- **Dynamically add** new scam tactics via YAML + script (no code deploy for regex rules).
- **Report** new patterns via `POST /reports/scam` (stored in DynamoDB for review).

### What it does NOT do yet (gap for Codex to build)

- **Live web retrieval** per user query (search careers page + fraud page at request time).
- **LLM verification with fresh context** (RAG over fetched pages) for arbitrary companies.
- **Role-level match** (“this job title doesn’t exist on official board”).
- **Full process verification** (“is Calendly interview normal for this company?”).
- Hindi/Hinglish corpus. ScamBench message-level data.

---

## Repository layout (data module)

```
data/
  employer_registry.yaml      # 47 companies — add employers here
  scam_tactics_registry.yaml  # 12 tactics — add patterns here
  manual_snapshots/           # Verified HTML when live fetch fails
  raw/<source_id>/<date>/     # Immutable downloads
  curated/                    # ETL outputs
  reports/                    # fetch_report.json, quality reports
  private/                    # Gmail T3 — never upload to public S3

scripts/
  fetch_sources.py            # Gov + base downloads
  fetch_employer_registry.py  # Policies + ATS from employer_registry.yaml
  run_etl.py                  # Full pipeline entrypoint
  build_deploy_bundle.py      # Slim bundle for AWS
  upload_deploy_bundle.py     # Push to S3 curated/
  register_scam_tactic.py     # Add/update tactic + optional rebuild
  creda/
    core.py                   # Normalize, PII redact, claims, dedupe
    pipeline.py               # Ingest orchestration
    employers.py              # Registry load, process profiles
    tactics.py                # Tactic compile + match

backend/
  intake/                     # API Gateway handlers
  worker/                     # SQS worker (deterministic + Strands)
  ingest/                     # Daily raw refresh
  shared/                     # S3, DynamoDB helpers

deploy/bundle/                # Pre-upload artifact
schemas/evidence.schema.json
docs/
  CODEX_HANDOFF.md            # This file
  AWS_DATA_HANDOFF.md         # AWS wiring details
  DYNAMIC_UPDATES.md          # Tactic/employer update workflow
```

---

## Configuration

### Prerequisites

```bash
cd /Users/siva/Documents/first_commit_hack
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional:
- **Kaggle API** — EMSCAD re-fetch (`~/.kaggle/kaggle.json`)
- **HF_TOKEN** — ScamBench download (`export HF_TOKEN=...`)
- **AWS credentials** — deploy + S3 upload

### Key config files

| File | Purpose |
|---|---|
| `data/employer_registry.yaml` | Company list, policy URLs, ATS boards, aliases |
| `data/scam_tactics_registry.yaml` | Scam detection regex + user guidance |
| `data/source_registry.yaml` | Source provenance (partial — not all raw folders listed) |
| `infra/samconfig.toml.example` | SAM deploy params |
| `infra/template.yaml` | Stack: `BedrockModelId`, `StrandsLayerArn`, `PATTERN_VERSION` |

### Environment variables (Lambda)

| Variable | Set by | Meaning |
|---|---|---|
| `DATA_BUCKET` | SAM | S3 bucket for `curated/*` bundle |
| `CASES_TABLE` | SAM | DynamoDB cases + reports |
| `CASE_QUEUE_URL` | SAM | Intake → worker queue |
| `BEDROCK_MODEL_ID` | SAM | Default Haiku model |
| `PATTERN_VERSION` | SAM | Tactic version key in DynamoDB |
| `DISABLE_STRANDS` | Manual on worker | Skip Bedrock; deterministic only |
| `VITE_API_URL` | Amplify | Frontend → API URL |

---

## Build and run (local)

### Full refresh pipeline

```bash
source .venv/bin/activate

# 1. Download gov sources + base raw files
python scripts/fetch_sources.py

# 2. Download employer policies + ATS boards from registry
python scripts/fetch_employer_registry.py

# 3. ETL → data/curated/*
python scripts/run_etl.py

# 4. Build Lambda-friendly bundle
python scripts/build_deploy_bundle.py

# 5. Verify counts
python -c "import json; print(json.load(open('deploy/bundle/manifest.json'))['counts'])"
```

Expected bundle counts:

```json
{
  "employer_policies": 10,
  "employers_in_registry": 47,
  "vacancies": 1000,
  "channel_patterns": 26,
  "recruiting_process_patterns": 10,
  "scam_tactics": 12,
  "demo_cases": 3
}
```

### Test deterministic logic locally

```bash
bash scripts/prepare_lambdas.sh   # copies shared/ into Lambda dirs

python <<'PY'
import json, sys
sys.path.insert(0, "backend/worker")
from deterministic import run_deterministic_checks

pol = [json.loads(l) for l in open("deploy/bundle/employer_policies.jsonl")]
ch  = [json.loads(l) for l in open("deploy/bundle/channel_patterns.jsonl")]
tac = [json.loads(l) for l in open("deploy/bundle/scam_tactics.jsonl")]
proc = [json.loads(l) for l in open("deploy/bundle/recruiting_process_patterns.jsonl")]
idx = json.load(open("deploy/bundle/employer_index.json"))

text = "TCS selected you. Pay security deposit INR 5000. Interview on WhatsApp."
_, _, verdict, tactics = run_deterministic_checks(
    text, "careers@gmail.com", "TCS", pol, ch, tac, proc, idx
)
print(verdict, [t["tactic_id"] for t in tactics])  # expect high_risk
PY
```

### AWS deploy

```bash
bash scripts/deploy.sh
# Then upload bundle:
python scripts/upload_deploy_bundle.py --bucket <DataBucketName from stack output>

curl -s "$API_URL/health" | jq .
# Must show: ok: true, dataReady: true
```

Connect Amplify to `frontend/` with `VITE_API_URL=$API_URL`.

---

## API surface (for building on top)

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `dataReady`, coverage counts |
| GET | `/coverage` | Employer + tactic counts from manifest |
| GET | `/tactics` | Full `scam_tactics.jsonl` as JSON |
| POST | `/cases` | `{ caseId, accessToken, status: queued }` |
| GET | `/cases/{id}` | Result with `verdict`, `evidence`, `matchedTactics`, `headline` |
| POST | `/reports/scam` | Log new pattern for review `{ reportId }` |

Case result shape (worker output):

```json
{
  "verdict": "high_risk | no_conflict_found | unverified",
  "headline": "One-sentence explanation",
  "matchedTactics": [
    {
      "tactic_id": "fee_or_deposit_request",
      "display_name": "Upfront fee or security deposit",
      "severity": "high",
      "user_guidance": "Legitimate employers do not charge..."
    }
  ],
  "evidence": [
    {
      "tier": 1,
      "check": "fee_policy",
      "outcome": "conflict",
      "sourceUrl": "https://...",
      "excerpt": "..."
    }
  ],
  "unresolved": ["We could not load an official policy snapshot for ..."]
}
```

---

## How to extend (Codex tasks)

### A. Add an employer

1. Edit `data/employer_registry.yaml`:

```yaml
  - employer_key: acme
    display_name: Acme Corp
    company_tier: startup
    regions: [us, india]
    scam_target_priority: high
    official_domains: [acme.com]
    official_careers_urls: [https://acme.com/careers]
    aliases: [acme, acme corp]
    policy:
      source_id: acme_recruitment_fraud_policy
      canonical_url: https://acme.com/careers/fraud-alert
      fetch:
        method: direct   # or wayback | manual
        url: https://acme.com/careers/fraud-alert
        filename: index.html
    ats:
      type: greenhouse
      board: acme
      source_id: greenhouse_acme_jobs
```

2. Add `SOURCE_META` entry in `scripts/creda/pipeline.py` for new `source_id`.
3. Run fetch → ETL → bundle (see Build section).

**Fetch methods:** `direct`, `wayback`, `manual` (file in `data/manual_snapshots/`).

### B. Add a scam tactic

```bash
python scripts/register_scam_tactic.py \
  --tactic-id qr_code_interview_fee \
  --name "QR code payment for interview slot" \
  --regex "scan.*qr" \
  --regex "pay.*interview.*qr" \
  --guidance "Real employers do not ask you to scan a QR code to pay for an interview." \
  --severity high \
  --category payment \
  --rebuild
```

Then upload bundle to S3 if deployed.

### C. Wire vacancy existence check (recommended)

**Where:** `backend/worker/deterministic.py`  
**Data:** `deploy/bundle/vacancy_index.jsonl` (already built)  
**Logic:** Extract role title from user paste → fuzzy match against `vacancy_index` for resolved `employer_key` → add T2 signal if no match.

### D. Live web retrieval pipeline (recommended major feature)

**Goal:** User names any company → fetch verified careers + fraud pages at query time → LLM compares offer to fresh context.

**Suggested architecture:**

```
POST /cases
  → Intake enqueues { caseId, employerHint, text }
  → Worker:
      1. resolve employer_key (employer_index.json + aliases)
      2. RETRIEVE (new module):
           - official_careers_urls from registry
           - try Greenhouse/Lever API if ats configured
           - fetch policy page (direct / wayback / cache)
           - cache in S3: live/{employer_key}/{date}/
      3. DETERMINISTIC (existing — always runs first)
      4. LLM (Strands/Bedrock):
           - prompt = user paste + retrieved snippets + matchedTactics
           - strict: cite only retrieved URLs; unverified if no T1
      5. Return verdict + evidence + matchedTactics + retrievedSources
```

**New files to create:**

| File | Purpose |
|---|---|
| `backend/worker/retrieve.py` | Fetch + extract careers/policy pages |
| `backend/shared/employer_resolve.py` | Hint → employer_key + URLs |
| `scripts/creda/extract_html.py` | Main-content extraction (reuse `core.parse_file_text`) |
| S3 prefix `live/` | Per-case retrieval cache (TTL 24h) |

**Do not remove:** deterministic-first path, T1/T2/T3 rules, pre-seeded bundle (fallback when live fetch fails).

### E. Promote user reports to tactics

1. Query DynamoDB `REPORT#*` items from `POST /reports/scam`.
2. Human or script review → `register_scam_tactic.py`.
3. Rebuild bundle + upload.

---

## Evidence tiers (do not break)

| Tier | Examples | Verdict use |
|---|---|---|
| T1 | Employer policies, gov advisories, official ATS vacancies | Can support **high_risk** on conflict |
| T2 | Derived signals (free mail, domain mismatch) | Supports; cannot alone confirm scam |
| T3 | EMSCAD, synthetic, Gmail, ScamBench | Research/eval only |

---

## Known blockers

| Source | Issue | Workaround |
|---|---|---|
| Infosys live policy | HTTP 403 | `data/manual_snapshots/infosys_recruitment_fraud_policy.html` |
| Google live fraud page | SPA, no text in HTML | Manual snapshot |
| TCS live policy | HTTP 403 | Wayback URL in registry |
| ScamBench | HF 401 | Set `HF_TOKEN`, re-run `fetch_sources.py` |
| FTC (old bot UA) | Was 403 | Fixed with browser User-Agent in `fetch_sources.py` |

---

## Related docs

- `docs/AWS_DATA_HANDOFF.md` — S3 keys, Lambda wiring, judge checklist  
- `docs/DYNAMIC_UPDATES.md` — Tactic + employer update commands  
- `DEPLOY.md` — Demo reliability, failure table  

---

## Suggested Codex prompt to start Phase D (live retrieval)

```
Read docs/CODEX_HANDOFF.md and implement backend/worker/retrieve.py:
- Resolve employer from deploy/bundle/employer_index.json + employer_aliases.json
- Fetch official careers page and policy URL (from registry or cache)
- Try Greenhouse API when ats.type=greenhouse
- Cache raw text to S3 live/{employer_key}/
- Pass snippets to existing deterministic checks + strands_explain
- Add retrievedSources[] to case result JSON
- Keep deterministic-first; unverified when fetch fails
- Add tests using TCS and Stripe hints
```

---

## Quick status summary

**Achieved:** Production-shaped static data pipeline, 47-company registry, 10 policies, 12 dynamic tactics, 1k vacancies, deterministic worker with user-facing tactic guidance, AWS-ready bundle, API for coverage/tactics/reports.

**Next:** Live retrieval + LLM-over-fresh-context layer on top of existing deterministic core — without replacing the bundle fallback.
