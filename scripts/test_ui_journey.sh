#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -d node_modules/playwright ]]; then
  npm install --no-save playwright@1.49.1
  npx playwright install chromium
fi
node scripts/test_ui_journey.mjs
