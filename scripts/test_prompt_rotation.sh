#!/usr/bin/env bash
# Back-compat wrapper — full catalog lives in test_cases.json + run_test_catalog.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$ROOT/scripts/run_test_catalog.sh"
