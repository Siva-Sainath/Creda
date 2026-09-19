# Creda deployment (judge-ready)

## Design principle: deterministic first, Strands second

Judges get a working verdict even if Bedrock is slow or throttled:

1. **Deterministic checks** always run (fee detection, free mailbox, policy conflict, channel patterns).
2. **Strands + Bedrock** adds the headline explanation when available.
3. **Pre-seeded S3 bundle** — Lambda never runs pandas ETL at runtime.

## Pre-deploy checklist

```bash
# Local
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_etl.py
python scripts/build_deploy_bundle.py   # creates deploy/bundle/ (~few MB)

# AWS (needs account + Bedrock model access in region)
bash scripts/deploy.sh
```

After deploy, verify:

```bash
curl -s "$API_URL/health" | jq .
# Must show: { "ok": true, "dataReady": true }
```

## Architecture

| Component | Role |
|---|---|
| **API Gateway + Intake Lambda** | POST /cases, GET /cases/{id}, GET /health |
| **SQS + Worker Lambda (Strands)** | Async verification; deterministic + Bedrock explanation |
| **S3** | Pre-uploaded `deploy/bundle/` at `curated/*` |
| **DynamoDB** | Cases, employer cache, pattern version |
| **EventBridge** | Daily ingest (lightweight raw refresh) |
| **Amplify** | Hosts `frontend/index.html` |

Glue is **optional post-MVP** for Athena audits — not on the judge critical path.

## Strands layer (recommended)

Set parameter on deploy:

```
StrandsLayerArn=arn:aws:lambda:REGION:856699698935:layer:strands-agents-py3_12-arm64:2
```

Or bundle `strands-agents` via `backend/worker/requirements.txt` (already included).

Set `DISABLE_STRANDS=true` on WorkerFunction only if Bedrock is unavailable — deterministic path still completes.

## Demo cases (built into bundle)

Three one-click demos in the UI:

1. Amazon + Gmail + fee → **high_risk**
2. KPMG + fee + WhatsApp → **high_risk**
3. Stripe + no fee → **no_conflict_found**

## If something fails during judging

| Symptom | Fix |
|---|---|
| `/health` dataReady false | Re-run `upload_deploy_bundle.py --bucket BUCKET` |
| Case stuck queued | Check SQS + Worker Lambda CloudWatch logs |
| Bedrock AccessDenied | Enable model in Bedrock console; or set DISABLE_STRANDS=true |
| CORS error | ApiUrl must match Amplify env; template allows `*` for hackathon |

## Cost controls

- DynamoDB on-demand, Lambda scales to zero
- Daily ingest: ~6 HTTP fetches, no heavy ETL
- Bedrock: Haiku model, 1 short call per case for headline only

Estimated weekend demo cost: **under $5** with free credits.
