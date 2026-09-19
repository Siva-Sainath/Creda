from __future__ import annotations

import json
import os
import secrets
import time
from typing import Any

import boto3

from shared.dynamo import get_case, new_access_token, new_case_id, put_case, table, token_hash
from shared.s3_data import load_coverage_stats, load_scam_tactics

sqs = boto3.client("sqs")
s3 = boto3.client("s3")


def _json(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }


def _check_data_ready() -> dict[str, Any]:
    bucket = os.environ.get("DATA_BUCKET", "")
    if not bucket:
        return {"dataReady": False, "reason": "DATA_BUCKET not set"}
    try:
        s3.head_object(Bucket=bucket, Key="curated/manifest.json")
        return {"dataReady": True}
    except Exception as exc:
        return {"dataReady": False, "reason": str(exc)}


def handler(event: dict, context: Any) -> dict:
    path = event.get("rawPath") or event.get("path") or ""
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "GET")

    if path.endswith("/health") and method == "GET":
        ready = _check_data_ready()
        stats = load_coverage_stats() if ready.get("dataReady") else {}
        return _json(200 if ready.get("dataReady") else 503, {"ok": ready.get("dataReady"), **ready, "coverage": stats.get("counts", {}), "service": "creda"})

    if path.endswith("/coverage") and method == "GET":
        stats = load_coverage_stats()
        emp_path = os.environ.get("DATA_BUCKET", "")
        employers = 0
        if emp_path:
            try:
                obj = s3.get_object(Bucket=emp_path, Key="curated/employer_index.json")
                idx = json.loads(obj["Body"].read().decode("utf-8"))
                employers = len(idx) if isinstance(idx, list) else 0
            except Exception:
                pass
        return _json(200, {"coverage": stats.get("counts", {}), "employers_in_registry": employers, "bundle_version": stats.get("bundle_version")})

    if path.endswith("/tactics") and method == "GET":
        tactics = load_scam_tactics()
        return _json(200, {"tactics": tactics, "count": len(tactics)})

    if path.endswith("/reports/scam") and method == "POST":
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _json(400, {"error": "invalid_json"})
        report_id = f"rep_{secrets.token_hex(4)}"
        tbl = table()
        tbl.put_item(
            Item={
                "pk": f"REPORT#{report_id}",
                "sk": "META",
                "status": "pending_review",
                "payloadJson": json.dumps(body),
                "createdAt": int(time.time()),
                "ttl": int(time.time()) + 30 * 86400,
            }
        )
        return _json(202, {"reportId": report_id, "message": "Report logged for tactic registry review"})

    if path.endswith("/cases") and method == "POST":
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return _json(400, {"error": "invalid_json"})

        text = (body.get("offerText") or body.get("text") or "").strip()
        if len(text) < 20:
            return _json(400, {"error": "text_too_short", "message": "Paste at least 20 characters of the offer."})
        if "offerText" not in body and text:
            body = {**body, "offerText": text}

        case_id = new_case_id()
        token = new_access_token()
        item = {
            "status": "queued",
            "stage": "Queued",
            "tokenHash": token_hash(token),
            "payloadJson": json.dumps(body),
            "patternVersion": os.environ.get("PATTERN_VERSION", "v1"),
            "createdAt": int(time.time()),
            "ttl": int(time.time()) + 7 * 86400,
        }
        put_case(case_id, "REV#0", item)

        queue_url = os.environ["CASE_QUEUE_URL"]
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"caseId": case_id}))

        return _json(202, {"caseId": case_id, "accessToken": token, "status": "queued"})

    if "/cases/" in path and method == "GET":
        case_id = path.rstrip("/").split("/")[-1]
        headers = event.get("headers") or {}
        token = headers.get("x-case-token") or headers.get("X-Case-Token")
        case = get_case(case_id)
        if not case:
            return _json(404, {"error": "not_found"})
        if not token or token_hash(token) != case.get("tokenHash"):
            return _json(401, {"error": "unauthorized"})

        if case.get("resultJson"):
            result = json.loads(case["resultJson"])
            return _json(200, result)

        return _json(
            200,
            {
                "status": case.get("status", "queued"),
                "stage": case.get("stage", "Queued"),
                "verdict": None,
                "headline": None,
                "claims": [],
                "evidence": [],
                "unresolved": [],
                "nextActions": [],
                "patternVersion": case.get("patternVersion", "v1"),
            },
        )

    return _json(404, {"error": "not_found"})
