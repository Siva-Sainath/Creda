from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3

from .config import CURATED_PREFIX, DATA_BUCKET

_s3 = boto3.client("s3")


def _key(path: str) -> str:
    return f"{CURATED_PREFIX}/{path}"


@lru_cache(maxsize=1)
def load_jsonl_from_s3(filename: str) -> tuple[dict[str, Any], ...]:
    if not DATA_BUCKET:
        return tuple()
    try:
        obj = _s3.get_object(Bucket=DATA_BUCKET, Key=_key(filename))
        rows = []
        for line in obj["Body"].read().decode("utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return tuple(rows)
    except Exception:
        return tuple()


def load_evidence_by_employer(employer_hint: str) -> list[dict[str, Any]]:
    hint = employer_hint.lower()
    policies = load_jsonl_from_s3("employer_policies.jsonl")
    return [p for p in policies if hint in (p.get("title") or "").lower() or hint in (p.get("source_id") or "").lower()]


def load_channel_patterns() -> list[dict[str, Any]]:
    return list(load_jsonl_from_s3("channel_patterns.jsonl"))


def load_recruiting_process_patterns() -> list[dict[str, Any]]:
    return list(load_jsonl_from_s3("recruiting_process_patterns.jsonl"))


def load_scam_tactics() -> list[dict[str, Any]]:
    return list(load_jsonl_from_s3("scam_tactics.jsonl"))


def load_employer_index() -> list[dict[str, Any]]:
    if not DATA_BUCKET:
        return []
    try:
        obj = _s3.get_object(Bucket=DATA_BUCKET, Key=_key("employer_index.json"))
        data = json.loads(obj["Body"].read().decode("utf-8"))
        return data if isinstance(data, list) else data.get("employers", [])
    except Exception:
        return []


def load_coverage_stats() -> dict[str, Any]:
    if not DATA_BUCKET:
        return {"dataReady": False}
    try:
        manifest = _s3.get_object(Bucket=DATA_BUCKET, Key=_key("manifest.json"))
        return json.loads(manifest["Body"].read().decode("utf-8"))
    except Exception:
        return {"dataReady": False}


def load_vacancies_for_employer(employer_hint: str) -> list[dict[str, Any]]:
    hint = employer_hint.lower()
    # Scan official vacancy records from evidence index if present
    try:
        obj = _s3.get_object(Bucket=DATA_BUCKET, Key=_key("vacancy_index.jsonl"))
        out = []
        for line in obj["Body"].read().decode("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if hint in (row.get("employer_claimed") or "").lower() or hint in (row.get("source_id") or "").lower():
                out.append(row)
        return out
    except Exception:
        return []


def put_raw_snapshot(source_id: str, retrieval_date: str, filename: str, body: bytes, content_type: str = "application/octet-stream") -> str:
    key = f"raw/{source_id}/{retrieval_date}/{filename}"
    _s3.put_object(Bucket=DATA_BUCKET, Key=key, Body=body, ContentType=content_type)
    return key


def put_manifest(retrieval_date: str, manifest: dict[str, Any]) -> str:
    key = f"manifests/{retrieval_date}/ingestion.json"
    _s3.put_object(Bucket=DATA_BUCKET, Key=key, Body=json.dumps(manifest, indent=2).encode("utf-8"), ContentType="application/json")
    return key
