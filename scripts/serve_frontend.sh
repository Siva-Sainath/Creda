#!/usr/bin/env bash
# Serve the MVP frontend locally (already points at deployed Mumbai API).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8080}"
echo "Creda MVP frontend: http://127.0.0.1:${PORT}/"
echo "API: https://x1ed4uf5q9.execute-api.ap-south-1.amazonaws.com"
cd "$ROOT/frontend"
python3 -m http.server "$PORT"
