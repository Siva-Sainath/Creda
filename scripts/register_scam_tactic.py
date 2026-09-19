#!/usr/bin/env python3
"""Register a newly discovered scam tactic and rebuild curated outputs."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from creda.tactics import add_tactic  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Add or update a scam tactic in the dynamic registry")
    parser.add_argument("--tactic-id", required=True)
    parser.add_argument("--name", required=True, help="Human-readable tactic name")
    parser.add_argument("--regex", action="append", required=True, help="Detection regex (repeatable)")
    parser.add_argument("--guidance", required=True, help="User-facing explanation")
    parser.add_argument("--severity", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--category", default="unknown")
    parser.add_argument("--region", action="append", default=["global"])
    parser.add_argument("--source-id", action="append", default=["user_report"])
    parser.add_argument("--rebuild", action="store_true", help="Run ETL + deploy bundle after update")
    args = parser.parse_args()

    entry = add_tactic(
        args.tactic_id,
        args.name,
        args.regex,
        args.guidance,
        severity=args.severity,
        category=args.category,
        regions=args.region,
        source_ids=args.source_id,
    )
    print(f"Registered tactic: {entry['tactic_id']} (updated {entry['last_updated']})")

    if args.rebuild:
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "run_etl.py")])
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "build_deploy_bundle.py")])
        print("Rebuilt curated data and deploy bundle.")


if __name__ == "__main__":
    main()
