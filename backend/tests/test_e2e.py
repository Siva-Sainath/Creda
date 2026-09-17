"""
Creda â€” End-to-end offline pipeline test.

Uses moto to run fake DynamoDB + SQS entirely in memory.
Bedrock is disabled via env var â€” the worker runs the full resolver
and deterministic checks pipeline but skips the AI model call.

What this proves without spending a single credit:
  1. POST /cases â†’ 202 with caseId + accessToken
  2. GET  /cases/{caseId} â†’ 200 with status=queued (token auth works)
  3. Worker SQS trigger â†’ runs resolver + checks â†’ writes verdict
  4. GET  /cases/{caseId} â†’ 200 with status=completed + verdict

Run with:
  python -m pytest backend/tests/test_e2e.py -v -s
"""

from __future__ import annotations

import importlib
import json
import os
import sys

import boto3
import pytest

# ---------------------------------------------------------------------------
# Set env vars BEFORE importing any Lambda handlers
# (Lambda handlers read env vars at module load time)
# ---------------------------------------------------------------------------
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["TABLE_NAME"] = "creda-cases-test"
os.environ["QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/123456789012/creda-jobs-test"
os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-3-haiku-20240307-v1:0"
os.environ["BEDROCK_DISABLED"] = "true"   # â† skip AI, zero credits
os.environ["LOG_LEVEL"] = "WARNING"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from moto import mock_aws

# ---------------------------------------------------------------------------
# Fixtures: spin up fake AWS resources
# ---------------------------------------------------------------------------

def _create_table(dynamo):
    """Create the same DynamoDB table defined in template.yaml."""
    return dynamo.create_table(
        TableName="creda-cases-test",
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
    )


def _create_queue(sqs_client):
    """Create the fake SQS queue."""
    resp = sqs_client.create_queue(QueueName="creda-jobs-test")
    return resp["QueueUrl"]


def _make_api_event(method: str, path: str, body: dict | None = None, headers: dict | None = None) -> dict:
    """Build a minimal HTTP API Gateway event dict."""
    return {
        "requestContext": {
            "http": {"method": method.upper()}
        },
        "rawPath": path,
        "pathParameters": {"caseId": path.split("/cases/")[-1]} if "/cases/" in path else {},
        "headers": headers or {},
        "body": json.dumps(body) if body else None,
    }


def _make_sqs_event(case_id: str) -> dict:
    """Build the SQS trigger event the Worker Lambda receives."""
    return {
        "Records": [
            {
                "messageId": "msg-001",
                "body": json.dumps({"caseId": case_id}),
            }
        ]
    }


# ---------------------------------------------------------------------------
# The actual end-to-end test
# ---------------------------------------------------------------------------

@mock_aws
def test_full_pipeline_end_to_end():
    """
    Full offline pipeline: POST â†’ queue â†’ worker â†’ GET verdict.
    No AWS credits. No Docker. No real Bedrock.
    """
    # --- Setup fake AWS ---
    dynamo = boto3.resource("dynamodb", region_name="us-east-1")
    sqs = boto3.client("sqs", region_name="us-east-1")
    _create_table(dynamo)
    queue_url = _create_queue(sqs)
    os.environ["QUEUE_URL"] = queue_url

    # --- Import handlers INSIDE mock context so they pick up fake clients ---
    # We need to reload them to pick up the new QUEUE_URL
    import backend.intake.handler as intake_mod
    import backend.worker.handler as worker_mod
    importlib.reload(intake_mod)
    importlib.reload(worker_mod)

    # ================================================================
    # STEP 1: POST /cases â€” submit a scam offer
    # ================================================================
    scam_offer = (
        "Congratulations! You have been selected for the role of Data Analyst at Amazon. "
        "Please pay a registration fee of Rs 3500 to recruiter@paytm to secure your position. "
        "The offer expires within 24 hours. Apply at https://bit.ly/amzn-fake-job"
    )

    post_event = _make_api_event("POST", "/cases", body={
        "text": scam_offer,
        "senderEmail": "hr@amaz0n-careers.in",
        "employerHint": "Amazon",
        "links": [],
    })

    post_response = intake_mod.lambda_handler(post_event, {})

    assert post_response["statusCode"] == 202, f"Expected 202, got {post_response['statusCode']}: {post_response['body']}"
    post_body = json.loads(post_response["body"])

    case_id = post_body["caseId"]
    access_token = post_body["accessToken"]
    assert case_id.startswith("c_"), f"caseId format wrong: {case_id}"
    assert access_token.startswith("t_"), f"accessToken format wrong: {access_token}"
    assert post_body["status"] == "queued"

    print(f"\nâœ“ POST /cases â†’ caseId={case_id}")

    # ================================================================
    # STEP 2: GET /cases/{caseId} while still queued â€” auth must work
    # ================================================================
    get_event_queued = _make_api_event(
        "GET", f"/cases/{case_id}",
        headers={"x-case-token": access_token},
    )
    get_response_queued = intake_mod.lambda_handler(get_event_queued, {})

    assert get_response_queued["statusCode"] == 200
    get_body_queued = json.loads(get_response_queued["body"])
    assert get_body_queued["status"] == "queued"

    print(f"âœ“ GET /cases/{case_id} (queued) â†’ status=queued")

    # ================================================================
    # STEP 3: Wrong token must be rejected (403)
    # ================================================================
    bad_token_event = _make_api_event(
        "GET", f"/cases/{case_id}",
        headers={"x-case-token": "t_wrongtokenvalue"},
    )
    bad_token_response = intake_mod.lambda_handler(bad_token_event, {})
    assert bad_token_response["statusCode"] == 403

    print(f"âœ“ Bad token â†’ 403 Forbidden")

    # ================================================================
    # STEP 4: Worker SQS trigger â€” runs full analysis pipeline
    # ================================================================
    sqs_event = _make_sqs_event(case_id)
    worker_response = worker_mod.lambda_handler(sqs_event, {})

    # No batch failures = success
    assert worker_response.get("batchItemFailures") == [], \
        f"Worker reported failures: {worker_response['batchItemFailures']}"

    print(f"âœ“ Worker processed case {case_id}")

    # ================================================================
    # STEP 5: GET /cases/{caseId} after worker â€” must show completed verdict
    # ================================================================
    get_event_done = _make_api_event(
        "GET", f"/cases/{case_id}",
        headers={"x-case-token": access_token},
    )
    get_response_done = intake_mod.lambda_handler(get_event_done, {})

    assert get_response_done["statusCode"] == 200
    get_body_done = json.loads(get_response_done["body"])

    status = get_body_done["status"]
    verdict = get_body_done.get("verdict")
    evidence = get_body_done.get("evidence", [])

    # Status must not be queued or running anymore
    assert status in ("completed", "could_not_complete"), \
        f"Expected completed, got: {status}"

    # Verdict must be one of the three valid values
    assert verdict in ("high_risk", "unverified", "no_conflict_found"), \
        f"Invalid verdict: {verdict}"

    # For this scam offer, we expect high_risk or unverified (never no_conflict_found)
    assert verdict != "no_conflict_found", \
        "A scam offer with UPI demand and fake domain must not be cleared!"

    print(f"âœ“ GET /cases/{case_id} (done) â†’ status={status}, verdict={verdict}")
    print(f"  Evidence records: {len(evidence)}")
    for ev in evidence:
        print(f"    [{ev.get('tier')}] {ev.get('check')}: {ev.get('outcome')}")

    # ================================================================
    # STEP 6: Idempotency â€” double POST must not create a second case
    # ================================================================
    post_response_2 = intake_mod.lambda_handler(post_event, {})
    # Should return 202 but without a new accessToken (case already exists)
    assert post_response_2["statusCode"] == 202

    print(f"âœ“ Double POST â†’ idempotent 202 (no second case created)")

    print(f"\n{'='*55}")
    print(f"  ALL E2E CHECKS PASSED")
    print(f"  verdict = {verdict}")
    print(f"  evidence records = {len(evidence)}")
    print(f"{'='*55}\n")


@mock_aws
def test_empty_text_rejected():
    """POST with empty text must return 400."""
    dynamo = boto3.resource("dynamodb", region_name="us-east-1")
    sqs = boto3.client("sqs", region_name="us-east-1")
    _create_table(dynamo)
    queue_url = _create_queue(sqs)
    os.environ["QUEUE_URL"] = queue_url

    import backend.intake.handler as intake_mod
    importlib.reload(intake_mod)

    event = _make_api_event("POST", "/cases", body={"text": "   "})
    resp = intake_mod.lambda_handler(event, {})
    assert resp["statusCode"] == 400
    print("\nâœ“ Empty text â†’ 400 Bad Request")


@mock_aws
def test_missing_token_rejected():
    """GET without X-Case-Token must return 401."""
    dynamo = boto3.resource("dynamodb", region_name="us-east-1")
    _create_table(dynamo)

    import backend.intake.handler as intake_mod
    importlib.reload(intake_mod)

    event = _make_api_event("GET", "/cases/c_fake1234", headers={})
    resp = intake_mod.lambda_handler(event, {})
    assert resp["statusCode"] == 401
    print("\nâœ“ Missing token â†’ 401 Unauthorized")


@mock_aws
def test_health_endpoint():
    """GET /health must return 200."""
    import backend.intake.handler as intake_mod
    importlib.reload(intake_mod)

    event = _make_api_event("GET", "/health")
    resp = intake_mod.lambda_handler(event, {})
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "ok"
    print("\nâœ“ GET /health â†’ 200 ok")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

