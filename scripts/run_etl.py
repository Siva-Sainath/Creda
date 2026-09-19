#!/usr/bin/env python3
"""Reproducible Creda ETL entry point: fetch sources, preprocess, validate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from creda.pipeline import run_pipeline  # noqa: E402


def main() -> int:
    fetch_report = ROOT / "data" / "reports" / "fetch_report.json"
    retrieval = None
    if fetch_report.exists():
        retrieval = json.loads(fetch_report.read_text()).get("retrieval_date")

    result = run_pipeline(retrieval=retrieval)
    print(json.dumps(result, indent=2, default=str))
    if result.get("validation", {}).get("error_count", 0) > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
