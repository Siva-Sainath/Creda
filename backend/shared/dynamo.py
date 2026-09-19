from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from typing import Any

import boto3

TABLE = os.environ.get("CASES_TABLE", "")


def table():
    return boto3.resource("dynamodb").Table(TABLE)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_case_id() -> str:
    return f"c_{secrets.token_hex(4)}"


def new_access_token() -> str:
    return f"t_{secrets.token_urlsafe(24)}"


def put_case(case_id: str, rev: str, item: dict[str, Any]) -> None:
    table().put_item(Item={"pk": f"CASE#{case_id}", "sk": rev, **item})


def get_case(case_id: str, rev: str = "REV#0") -> dict[str, Any] | None:
    resp = table().get_item(Key={"pk": f"CASE#{case_id}", "sk": rev})
    return resp.get("Item")


def update_case_status(case_id: str, status: str, stage: str, extra: dict[str, Any] | None = None) -> None:
    expr = "SET #s = :s, stage = :stage, updatedAt = :u"
    names = {"#s": "status"}
    values: dict[str, Any] = {":s": status, ":stage": stage, ":u": int(time.time())}
    if extra:
        for k, v in extra.items():
            expr += f", {k} = :{k}"
            values[f":{k}"] = v
    table().update_item(
        Key={"pk": f"CASE#{case_id}", "sk": "REV#0"},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def bedrock_enabled() -> bool:
    try:
        item = table().get_item(Key={"pk": "CONTROL#BEDROCK", "sk": "META"}).get("Item")
        return item is None or item.get("status", "enabled") == "enabled"
    except Exception:
        return True


def get_employer_cache(domain: str) -> dict[str, Any] | None:
    resp = table().get_item(Key={"pk": f"EMPLOYER#{domain}", "sk": "PROFILE"})
    return resp.get("Item")


def put_employer_cache(domain: str, profile: dict[str, Any], ttl_days: int = 7) -> None:
    table().put_item(
        Item={
            "pk": f"EMPLOYER#{domain}",
            "sk": "PROFILE",
            "ttl": int(time.time()) + ttl_days * 86400,
            **profile,
        }
    )


def get_active_patterns() -> dict[str, Any]:
    resp = table().get_item(Key={"pk": "PATTERNS#active", "sk": f"VERSION#{os.environ.get('PATTERN_VERSION', 'v1')}"})
    item = resp.get("Item")
    if item:
        return item
    return {"rules": [], "sourceIds": [], "version": os.environ.get("PATTERN_VERSION", "v1")}


def put_source_version(source_id: str, version: int, meta: dict[str, Any]) -> None:
    table().put_item(Item={"pk": f"SOURCE#{source_id}", "sk": f"VERSION#{version}", **meta})


def dumps(obj: Any) -> str:
    return json.dumps(obj, default=str)
