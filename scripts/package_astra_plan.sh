#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ASTRA_DIR="$ROOT/docs/astra"
ZIP_PATH="$ASTRA_DIR/creda-astra-plan.zip"

cd "$ASTRA_DIR"

rm -f "$ZIP_PATH"
zip -j "$ZIP_PATH" ./*.md

echo "Wrote $ZIP_PATH"
echo "Files:"
unzip -l "$ZIP_PATH"
