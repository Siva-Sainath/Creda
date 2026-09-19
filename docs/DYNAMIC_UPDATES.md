# Dynamic scam tactic updates

Creda keeps scam patterns in a **versioned registry** that you can update without redeploying Lambda code.

## Registry files

| File | Purpose |
|---|---|
| `data/scam_tactics_registry.yaml` | Source of truth for detection rules and user guidance |
| `data/curated/scam_tactics.jsonl` | Compiled tactics after ETL |
| `deploy/bundle/scam_tactics.jsonl` | What the worker reads at runtime (upload to S3) |
| `data/employer_registry.yaml` | 50+ employers across big tech, India IT, startups |
| `data/curated/employer_index.json` | Coverage matrix (policy + ATS flags) |

## Add a newly discovered scam tactic

```bash
python scripts/register_scam_tactic.py \
  --tactic-id ai_interview_bot_fee \
  --name "Paid AI interview platform fee" \
  --regex "ai interview platform" \
  --regex "pay.*interview.*link" \
  --guidance "Legitimate employers do not ask you to pay for an AI interview platform link." \
  --severity high \
  --category payment \
  --region india \
  --region global \
  --rebuild
```

Then upload the bundle:

```bash
python scripts/upload_deploy_bundle.py --bucket YOUR_BUCKET
```

## Expand employer coverage

1. Add an entry to `data/employer_registry.yaml` (policy URL, Wayback URL, or Greenhouse board token).
2. Run:

```bash
python scripts/fetch_employer_registry.py
python scripts/run_etl.py
python scripts/build_deploy_bundle.py
```

## User-facing report endpoint

Users can submit new patterns via API (stored for review):

```bash
curl -X POST "$API/reports/scam" \
  -H "Content-Type: application/json" \
  -d '{"text":"They asked for UPI for HR verification","employerHint":"Infosys","notes":"New variant"}'
```

Review pending reports in DynamoDB (`REPORT#*`), then promote to `scam_tactics_registry.yaml` using `register_scam_tactic.py`.

## List active tactics

```bash
curl -s "$API/tactics" | jq '.count'
curl -s "$API/coverage" | jq .
```
