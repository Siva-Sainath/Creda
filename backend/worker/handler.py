from __future__ import annotations

import json
import traceback
from typing import Any

from shared.dynamo import get_case, update_case_status

from .agent import (
    get_channels,
    get_employer_index,
    get_hiring_pipeline_profiles,
    get_policies,
    get_recruiting_patterns,
    get_tactics,
    strands_explain,
)
from .deterministic import extract_claims, run_deterministic_checks


def process_case(case_id: str) -> dict[str, Any]:
    case = get_case(case_id)
    if not case:
        raise ValueError(f"Case not found: {case_id}")

    payload = json.loads(case.get("payloadJson", "{}"))
    text = payload.get("offerText") or payload.get("text", "")
    sender = payload.get("senderEmail", "")
    employer_hint = payload.get("employerHint", "")

    update_case_status(case_id, "running", "Running deterministic checks")

    policies = get_policies()
    channels = get_channels()
    tactics = get_tactics()
    process_patterns = get_recruiting_patterns()
    hiring_pipeline_profiles = get_hiring_pipeline_profiles()
    employer_index = get_employer_index()
    claims = extract_claims(text)
    evidence, unresolved, verdict, matched_tactics = run_deterministic_checks(
        text,
        sender,
        employer_hint,
        policies,
        channels,
        tactics,
        process_patterns,
        employer_index,
        hiring_pipeline_profiles,
    )

    update_case_status(case_id, "running", "Generating explanation")
    headline = strands_explain({"claims": claims, "matchedTactics": matched_tactics}, evidence, verdict)

    status = "completed" if verdict else "could_not_complete"
    if verdict == "unverified":
        status = "needs_evidence"

    result = {
        "status": status,
        "stage": "Complete",
        "verdict": verdict,
        "headline": headline,
        "claims": claims,
        "evidence": evidence,
        "matchedTactics": matched_tactics,
        "unresolved": unresolved,
        "nextActions": _next_actions(evidence, employer_hint, matched_tactics),
        "patternVersion": case.get("patternVersion", "v1"),
    }

    update_case_status(
        case_id,
        status,
        "Complete",
        {
            "verdict": verdict or "",
            "headline": headline,
            "resultJson": json.dumps(result),
            "claimsJson": json.dumps(claims),
            "evidenceJson": json.dumps(evidence),
        },
    )
    return result


def _next_actions(evidence: list[dict], employer_hint: str, matched_tactics: list[dict] | None = None) -> list[dict[str, Any]]:
    actions = []
    for ev in evidence:
        if ev.get("sourceUrl"):
            actions.append({"label": "View official source", "url": ev["sourceUrl"]})
            break
    for tac in (matched_tactics or [])[:2]:
        if tac.get("user_guidance"):
            actions.append({"label": tac.get("display_name", "Scam pattern"), "url": "#tactic-" + tac.get("tactic_id", "")})
    if employer_hint:
        actions.append({"label": f"Search official careers page for {employer_hint}", "url": f"https://www.google.com/search?q={employer_hint}+careers+official"})
    return actions[:4]


def handler(event: dict, context: Any) -> dict:
    failures = []
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            process_case(body["caseId"])
        except Exception as exc:
            failures.append({"itemIdentifier": record["messageId"]})
            print(json.dumps({"error": str(exc), "trace": traceback.format_exc()}))
    return {"batchItemFailures": failures}
