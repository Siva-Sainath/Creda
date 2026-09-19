#!/usr/bin/env bash
# Full live regression — API catalog + local vacancy unit checks.
# Safe to re-run anytime against prod; does not tune verdicts or add UI demo chips.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API="${CREDA_API_URL:-https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com}"
FAIL=0

echo "╔══════════════════════════════════════════╗"
echo "║  Creda live test suite                   ║"
echo "╚══════════════════════════════════════════╝"
echo "API: $API"
echo ""

echo "==> [1/3] API catalog (all cases + follow-ups + OCR + intake guards)"
CREDA_API_URL="$API" bash "$ROOT/scripts/run_test_catalog.sh" || FAIL=1

echo ""
echo "==> [2/3] Vacancy identity unit checks (local, no network)"
bash "$ROOT/scripts/test_vacancy_identity.sh" || FAIL=1
bash "$ROOT/scripts/test_vacancy_evidence.sh" || FAIL=1

echo ""
echo "==> [3/3] Browser UI journey (subset tagged ui — optional)"
if command -v node >/dev/null && [[ -f "$ROOT/scripts/test_ui_journey.mjs" ]]; then
  if node -e "require('playwright')" 2>/dev/null; then
    CREDA_UI_URL="${CREDA_UI_URL:-https://main.d32sg54oqu2gcb.amplifyapp.com}" \
      node "$ROOT/scripts/test_ui_journey.mjs" || FAIL=1
  else
    echo "SKIP UI journey: playwright not installed (npm i -D playwright && npx playwright install chromium)"
  fi
else
  echo "SKIP UI journey: node/playwright unavailable"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  echo "LIVE SUITE PASSED"
  exit 0
fi
echo "LIVE SUITE FAILED"
exit 1
