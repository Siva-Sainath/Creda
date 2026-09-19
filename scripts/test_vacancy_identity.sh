#!/usr/bin/env bash
set -euo pipefail
ROOT="/Users/siva/Documents/Codex/2026-09-17/creda-aws-backend/outputs/creda-backend/src"
python3 <<PY
import json, sys
sys.path.insert(0, "${ROOT}")
from vacancy_identity import match_vacancy_rows, vacancy_identity
vac=[json.loads(l) for l in open("/Users/siva/Documents/first_commit_hack/deploy/bundle/vacancy_index.jsonl")]
link="https://stripe.com/jobs/search?gh_jid=8172510"
rows=[{"employer_claimed":"Stripe","canonical_url":r["canonical_url"]} for r in vac if r.get("employer_claimed")=="Stripe"]
m=match_vacancy_rows("stripe",[link],rows)
assert m and "8172510" in m[0]["canonical_url"], m
print("OK exact gh_jid match for Stripe 8172510")
PY
