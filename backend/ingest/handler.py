from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3
import requests

from shared.dynamo import put_source_version
from shared.s3_data import put_manifest, put_raw_snapshot

HEADERS = {"User-Agent": "CredaIngest/1.0", "Accept": "*/*"}

# Lightweight daily refresh — no pandas/pyarrow in Lambda
DAILY_SOURCES = [
    ("amazon_recruitment_fraud_policy", "https://amazon.jobs/content/en/how-we-hire/fraud-alert-india", "index.html"),
    ("google_recruitment_fraud_policy", "https://careers.google.com/how-we-hire/recruitment-fraud/", "index.html"),
    ("kpmg_recruitment_fraud_policy", "https://kpmg.com/in/en/media/press-releases/2024/12/important-recruitment-fraud-alert.html", "index.html"),
    ("wipro_recruitment_fraud_policy", "https://careers.wipro.com/content/Recruitment-Fraud-Alert/?locale=en_US", "index.html"),
    ("greenhouse_stripe_jobs", "https://boards-api.greenhouse.io/v1/boards/stripe/jobs", "jobs.json"),
    ("i4c_captcha_advisory_2025", "https://cybercrime.gov.in/Webform/theme/resources/advisories/ADVISORY%20TAU-ADV-004_Captcha%20Filling%20Fraud_08.04.2025.pdf", "advisory.pdf"),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def handler(event: dict, context: Any) -> dict:
    retrieval = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results = []
    for source_id, url, filename in DAILY_SOURCES:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=45)
            if resp.status_code >= 400 or len(resp.content) < 100:
                results.append({"source_id": source_id, "status": "failed", "http": resp.status_code})
                continue
            checksum = sha256_bytes(resp.content)
            key = put_raw_snapshot(source_id, retrieval, filename, resp.content)
            put_source_version(
                source_id,
                1,
                {
                    "publisher": source_id,
                    "url": url,
                    "hash": checksum,
                    "fetchedAt": retrieval,
                    "approvalStatus": "auto_snapshot",
                    "s3Key": key,
                },
            )
            results.append({"source_id": source_id, "status": "downloaded", "checksum": checksum, "s3Key": key})
        except Exception as exc:
            results.append({"source_id": source_id, "status": "error", "detail": str(exc)})

    manifest = {
        "retrieval_date": retrieval,
        "downloaded": sum(1 for r in results if r.get("status") == "downloaded"),
        "failed": sum(1 for r in results if r.get("status") != "downloaded"),
        "results": results,
        "note": "Curated bundle is pre-seeded at deploy; daily job refreshes raw T1 snapshots only.",
    }
    manifest_key = put_manifest(retrieval, manifest)

    # Seed PATTERNS#active if missing
    table = boto3.resource("dynamodb").Table(os.environ["CASES_TABLE"])
    table.put_item(
        Item={
            "pk": "PATTERNS#active",
            "sk": f"VERSION#{os.environ.get('PATTERN_VERSION', 'v1')}",
            "rules": ["fee_or_deposit_request", "free_mailbox", "whatsapp_channel"],
            "sourceIds": [r["source_id"] for r in results if r.get("status") == "downloaded"],
            "evalResult": "deploy_seeded",
            "reviewer": "system",
        }
    )

    return {"statusCode": 200, "body": json.dumps({"manifest_key": manifest_key, **manifest})}
