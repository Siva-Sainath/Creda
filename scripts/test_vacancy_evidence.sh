#!/usr/bin/env bash
set -euo pipefail
ROOT="/Users/siva/Documents/Codex/2026-09-17/creda-aws-backend/outputs/creda-backend/src"
VENV="/tmp/creda-test-venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q email_validator rapidfuzz tldextract
fi
"$VENV/bin/python" <<PY
import json, sys
sys.path.insert(0, "${ROOT}")
from evidence_checks import vacancy_evidence

employer = {"employer_key": "stripe", "official_domains": ["stripe.com"]}
link = "https://stripe.com/jobs/search?gh_jid=8172510"
vacancies = [
    {"employer_claimed": "Stripe", "canonical_url": "https://stripe.com/jobs/search?gh_jid=8120185"},
    {"employer_claimed": "Stripe", "canonical_url": "https://stripe.com/jobs/search?gh_jid=8172510"},
]
ev = vacancy_evidence(employer, [link], vacancies)
assert ev and ev[0]["outcome"] == "match", ev
assert "8172510" in ev[0]["sourceUrl"], ev
assert "8120185" not in ev[0]["sourceUrl"], ev
print("OK vacancy_evidence uses gh_jid identity not path-only")

wrong_only = vacancy_evidence(employer, [link], [vacancies[0]])
assert wrong_only and wrong_only[0]["id"] == "ev_vacancy_not_in_feed", wrong_only
print("OK missing gh_jid returns not_in_feed not wrong match")
PY
