#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHARED="$ROOT/backend/shared"
for fn in intake worker ingest; do
  dest="$ROOT/backend/$fn/shared"
  rm -rf "$dest"
  cp -R "$SHARED" "$dest"
done
echo "Copied shared/ into intake, worker, ingest"
