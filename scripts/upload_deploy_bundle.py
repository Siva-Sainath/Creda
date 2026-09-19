#!/usr/bin/env python3
"""Upload deploy bundle to S3 (run after sam deploy or with bucket name)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "deploy" / "bundle"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="curated")
    args = parser.parse_args()

    s3 = boto3.client("s3")
    uploaded = []
    for path in sorted(BUNDLE.rglob("*")):
        if not path.is_file():
            continue
        key = f"{args.prefix}/{path.relative_to(BUNDLE).as_posix()}"
        s3.upload_file(str(path), args.bucket, key)
        uploaded.append(key)

    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    s3.put_object(
        Bucket=args.bucket,
        Key=f"manifests/{manifest['retrieval_date']}/ingestion.json",
        Body=json.dumps(manifest, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    print(json.dumps({"bucket": args.bucket, "uploaded": len(uploaded), "manifest_key": f"manifests/{manifest['retrieval_date']}/ingestion.json"}, indent=2))


if __name__ == "__main__":
    main()
