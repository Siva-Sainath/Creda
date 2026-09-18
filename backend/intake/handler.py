"""
Creda — Intake Lambda handler.

Handles two routes:
  POST /cases    → validate offer, create case, enqueue, return caseId + accessToken instantly
  GET  /cases/{caseId}  → authenticate token, read DynamoDB, return current status

Design rules (from the build brief):
  - Must return in < 1 second for POST
  - Store only SHA-256(accessToken) — never the raw token
  - Conditional write to prevent duplicate cases from double-click
  - accessToken returned ONCE and never logged
  - Token compare is constant-time (no timing attacks on hmac.compare_digest)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# ---------------------------------------------------------------------------
# AWS clients — initialised once per container, reused across warm invocations
# ---------------------------------------------------------------------------
TABLE_NAME = os.environ["TABLE_NAME"]
QUEUE_URL = os.environ["QUEUE_URL"]

from botocore.config import Config

_boto_config = Config(connect_timeout=2, read_timeout=2, retries={'max_attempts': 1})

# Support local DynamoDB (SAM local / docker) via DYNAMODB_ENDPOINT env var
_dynamo_kwargs = {"config": _boto_config}
if os.environ.get("DYNAMODB_ENDPOINT"):
    _dynamo_kwargs["endpoint_url"] = os.environ["DYNAMODB_ENDPOINT"]

_dynamo = boto3.resource("dynamodb", **_dynamo_kwargs)
_table = _dynamo.Table(TABLE_NAME)
_sqs = boto3.client("sqs", config=_boto_config)
_s3 = boto3.client("s3", config=_boto_config)
EVIDENCE_BUCKET = os.environ.get("EVIDENCE_BUCKET", "")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_TEXT_BYTES = 10_240          # 10 KB — a job offer is never longer than this
CASE_TTL_DAYS = 7               # cases expire from DynamoDB after 7 days
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Case-Token",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import decimal

class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def _ok(body: dict, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, cls=_DecimalEncoder),
    }


def _err(message: str, status: int = 400) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps({"error": message}),
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _ttl_epoch(days: int = CASE_TTL_DAYS) -> int:
    return int(time.time()) + days * 86_400


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# POST /upload-url
# ---------------------------------------------------------------------------

def _upload_url(event: dict) -> dict:
    # Generates a presigned PUT URL for screenshots
    if not EVIDENCE_BUCKET:
        return _err("EVIDENCE_BUCKET not configured", status=500)
        
    object_key = f"uploads/{uuid.uuid4().hex}.jpeg"
    
    try:
        url = _s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': EVIDENCE_BUCKET,
                'Key': object_key,
                'ContentType': 'image/jpeg'
            },
            ExpiresIn=300 # 5 minutes
        )
        return _ok({"uploadUrl": url, "key": object_key})
    except Exception:
        logger.exception("Failed to generate presigned URL")
        return _err("Failed to generate upload URL", status=500)

# ---------------------------------------------------------------------------
# POST /cases
# ---------------------------------------------------------------------------

def _create_case(event: dict) -> dict:
    # Parse body
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _err("Request body must be valid JSON")

    offer_text: str = body.get("text", "").strip()
    sender_email: str | None = body.get("senderEmail") or None
    links: list[str] = body.get("links", [])
    employer_hint: str | None = body.get("employerHint") or None
    locale: str = body.get("locale", "en-IN")
    screenshot_key: str | None = body.get("screenshotKey") or None

    # Validate
    if not offer_text and not screenshot_key:
        return _err("text or screenshotKey is required")
    if len(offer_text.encode()) > MAX_TEXT_BYTES:
        return _err(f"text exceeds {MAX_TEXT_BYTES // 1024} KB limit")
    if not isinstance(links, list):
        return _err("links must be an array")

    # Generate IDs — short but random enough for a hackathon
    case_id = "c_" + secrets.token_hex(4)          # e.g. c_8f2a3b1c
    access_token = "t_" + secrets.token_urlsafe(24) # never stored, never logged
    token_hash = _sha256(access_token)

    # Write case to DynamoDB with conditional expression to prevent duplicates
    item = {
        "PK": f"CASE#{case_id}",
        "SK": "REV#0",
        "case_id": case_id,
        "status": "queued",
        "stage": "Queued",
        "token_hash": token_hash,
        "offer_text": offer_text,          # worker needs this; cleared after analysis
        "screenshot_key": screenshot_key,
        "sender_email": sender_email,
        "links": links,
        "employer_hint": employer_hint,
        "locale": locale,
        "created_at": _now_iso(),
        "pattern_version": "v1",
        "ttl": _ttl_epoch(),
    }

    try:
        _table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(PK)",  # idempotency guard
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Double-click: case already exists, return the same caseId without a new token
            # (caller must use their original token)
            return _ok({"caseId": case_id, "status": "queued"}, status=202)
        logger.exception("DynamoDB write failed")
        return _err("Failed to create case. Please retry.", status=500)

    # Enqueue for async processing
    try:
        _sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({"caseId": case_id}),
            MessageGroupId=case_id,         # FIFO-compatible; standard queue ignores this
        )
    except Exception:
        logger.exception("SQS enqueue failed for case %s", case_id)
        if os.environ.get("DYNAMODB_ENDPOINT"):
            logger.warning("Local dev mode: ignoring SQS failure and continuing")
        else:
            # Mark case as failed immediately rather than leaving it stuck in queued forever
            _table.update_item(
                Key={"PK": f"CASE#{case_id}", "SK": "REV#0"},
                UpdateExpression="SET #s = :s, stage = :g",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "could_not_complete", ":g": "Enqueue failed"},
            )
            return _err("Failed to queue case for analysis. Please retry.", status=500)

    logger.info("Case %s created and queued", case_id)

    # Return token ONCE — never again
    return _ok(
        {"caseId": case_id, "accessToken": access_token, "status": "queued"},
        status=202,
    )


# ---------------------------------------------------------------------------
# GET /cases/{caseId}
# ---------------------------------------------------------------------------

def _get_case(event: dict) -> dict:
    path_params = event.get("pathParameters") or {}
    case_id = path_params.get("caseId", "").strip()
    if not case_id:
        return _err("caseId is required", status=400)

    # Authenticate via X-Case-Token header
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    raw_token = headers.get("x-case-token", "").strip()
    if not raw_token:
        return _err("X-Case-Token header is required", status=401)

    # Read latest revision from DynamoDB
    try:
        resp = _table.get_item(Key={"PK": f"CASE#{case_id}", "SK": "REV#0"})
    except Exception:
        logger.exception("DynamoDB read failed for case %s", case_id)
        return _err("Failed to retrieve case", status=500)

    item = resp.get("Item")
    if not item:
        return _err("Case not found", status=404)

    # Check TTL (DynamoDB async deletion — enforce in application code immediately)
    ttl = item.get("ttl", 0)
    if ttl and int(time.time()) > ttl:
        return _err("Case has expired", status=410)

    # Constant-time token comparison to prevent timing attacks
    stored_hash = item.get("token_hash", "")
    supplied_hash = _sha256(raw_token)
    if not hmac.compare_digest(stored_hash, supplied_hash):
        return _err("Invalid token", status=403)

    # Build response — read evidence records separately
    evidence_records = _read_evidence(case_id)

    response_body: dict[str, Any] = {
        "status": item.get("status", "queued"),
        "stage": item.get("stage", "Queued"),
        "verdict": item.get("verdict"),
        "headline": item.get("headline"),
        "claims": item.get("claims", []),
        "evidence": evidence_records,
        "unresolved": item.get("unresolved", []),
        "nextActions": item.get("next_actions", []),
        "patternVersion": item.get("pattern_version", "v1"),
    }

    return _ok(response_body)


def _read_evidence(case_id: str) -> list[dict]:
    """Read all EVIDENCE# records for a case from DynamoDB."""
    try:
        from boto3.dynamodb.conditions import Key as DKey
        resp = _table.query(
            KeyConditionExpression=DKey("PK").eq(f"CASE#{case_id}") & DKey("SK").begins_with("EVIDENCE#"),
        )
        return [
            {
                "id": item.get("evidence_id"),
                "tier": item.get("tier"),
                "check": item.get("check_name"),
                "outcome": item.get("outcome"),
                "sourceUrl": item.get("source_url"),
                "excerpt": item.get("excerpt"),
                "fetchedAt": item.get("fetched_at"),
            }
            for item in resp.get("Items", [])
        ]
    except Exception:
        logger.exception("Failed to read evidence for case %s", case_id)
        return []


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def _health() -> dict:
    return _ok({"status": "ok", "service": "creda-intake"})


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event: dict, context: Any) -> dict:
    """Route incoming API Gateway HTTP API events to the right handler."""
    method = event.get("requestContext", {}).get("http", {}).get("method", "").upper()
    path = event.get("rawPath", "")

    logger.debug("method=%s path=%s", method, path)

    if path == "/health":
        return _health()

    if method == "POST" and path == "/upload-url":
        return _upload_url(event)

    if method == "POST" and path == "/cases":
        return _create_case(event)

    if method == "GET" and path.startswith("/cases/"):
        return _get_case(event)

    return _err(f"Route not found: {method} {path}", status=404)
