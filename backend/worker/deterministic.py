from __future__ import annotations

import re
from typing import Any

from shared.hiring_pipelines import detect_pipeline_conflicts, fee_demand_in_text, resolve_hiring_pipeline

FREE_MAIL = {
    "gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "rediffmail.com",
    "proton.me", "protonmail.com", "googlemail.com", "live.com", "yahoo.co.uk",
}
FEE_RE = re.compile(
    r"\b(fee|fees|deposit|registration charge|security deposit|training fee|pay (?:inr|rs|₹|usd|\$)|upi|paytm|phonepe|gpay)\b",
    re.I,
)
IM_RE = re.compile(r"\b(whatsapp|whats app|telegram|signal messenger|t\.me/)\b", re.I)
CAPTCHA_TASK_RE = re.compile(r"\b(captcha filling|task scam|product boosting|commission task|click task)\b", re.I)
CRYPTO_GIFT_RE = re.compile(r"\b(bitcoin|usdt|crypto|gift card|google play card|steam card)\b", re.I)
DOC_EARLY_RE = re.compile(r"\b(bank account|aadhaar|aadhar|pan card|passport copy|ifsc|routing number)\b", re.I)


def extract_domain(email: str) -> str:
    if not email or "@" not in email:
        return ""
    return email.split("@", 1)[1].lower().strip()


def extract_claims(text: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if fee_demand_in_text(text or ""):
        m = FEE_RE.search(text or "")
        claims.append({"id": "cl_fee", "type": "payment_demand", "value": m.group(0) if m else "fee", "quote": (text or "")[:200]})
    if IM_RE.search(text or ""):
        claims.append({"id": "cl_im_channel", "type": "channel", "value": "instant_messaging", "quote": (text or "")[:200]})
    if CAPTCHA_TASK_RE.search(text or ""):
        claims.append({"id": "cl_captcha_task", "type": "task_scam", "value": "captcha_or_task", "quote": (text or "")[:200]})
    return claims


def resolve_policy(policies: list[dict[str, Any]], employer_hint: str, process_patterns: list[dict[str, Any]]) -> dict[str, Any] | None:
    hint = (employer_hint or "").lower().strip()
    if not hint:
        return None
    for p in policies:
        key = (p.get("employer_key") or "").lower()
        if key and key in hint:
            return p
    for p in policies:
        ek = (p.get("employer_key") or p.get("source_id", "").split("_")[0]).lower()
        if ek and ek in hint:
            return p
    for p in policies:
        if hint in (p.get("source_id") or "").lower() or hint in (p.get("display_name") or "").lower():
            return p
    for pp in process_patterns:
        if hint in (pp.get("display_name") or "").lower() or hint in (pp.get("employer_key") or ""):
            return pp
    return None


def match_scam_tactics(text: str, sender_email: str, tactics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    haystack = f"{text}\n{sender_email}".strip()
    matched = []
    for tac in tactics:
        for raw in tac.get("detection_regex") or []:
            try:
                if re.search(raw, haystack, re.I):
                    if tac.get("tactic_id") == "fee_or_deposit_request" and not fee_demand_in_text(haystack):
                        break
                    matched.append(
                        {
                            "tactic_id": tac.get("tactic_id"),
                            "display_name": tac.get("display_name"),
                            "severity": tac.get("severity", "medium"),
                            "user_guidance": tac.get("user_guidance", ""),
                            "category": tac.get("category"),
                        }
                    )
                    break
            except re.error:
                continue
    if sender_email and extract_domain(sender_email) in FREE_MAIL:
        if not any(t.get("tactic_id") == "free_mailbox_sender" for t in matched):
            fb = next((t for t in tactics if t.get("tactic_id") == "free_mailbox_sender"), None)
            if fb:
                matched.append(
                    {
                        "tactic_id": fb["tactic_id"],
                        "display_name": fb["display_name"],
                        "severity": fb.get("severity", "medium"),
                        "user_guidance": fb.get("user_guidance", ""),
                        "category": fb.get("category"),
                    }
                )
    return matched


def run_deterministic_checks(
    text: str,
    sender_email: str,
    employer_hint: str,
    policies: list[dict[str, Any]],
    channels: list[dict[str, Any]],
    tactics: list[dict[str, Any]] | None = None,
    process_patterns: list[dict[str, Any]] | None = None,
    employer_index: list[dict[str, Any]] | None = None,
    hiring_pipeline_profiles: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[str], str | None, list[dict[str, Any]]]:
    """Returns (evidence, unresolved, verdict, matched_tactics). Always completes without Bedrock."""
    evidence: list[dict[str, Any]] = []
    unresolved: list[str] = []
    process_patterns = process_patterns or []
    tactics = tactics or []
    employer_index = employer_index or []

    matched_policy = resolve_policy(policies, employer_hint, process_patterns)
    pipeline_profile = resolve_hiring_pipeline(hiring_pipeline_profiles or [], employer_hint, employer_index)
    if pipeline_profile and not matched_policy:
        matched_policy = _policy_from_pipeline(pipeline_profile)
    matched_tactics = match_scam_tactics(text, sender_email, tactics)

    sender_domain = extract_domain(sender_email)
    text_lower = (text or "").lower()
    fee_claim = fee_demand_in_text(text or "")

    if sender_domain:
        if sender_domain in FREE_MAIL:
            evidence.append(_ev("ev_free_mailbox", 2, "free_mailbox", "signal", "", f"Sender uses free mailbox domain {sender_domain}"))
        if matched_policy:
            official = [d for d in (matched_policy.get("official_domains") or []) if d and sender_domain not in d]
            if official and sender_domain not in official and not any(sender_domain.endswith(o.lstrip("@")) for o in official if "." in o):
                evidence.append(
                    _ev(
                        "ev_domain_mismatch",
                        2,
                        "sender_domain_mismatch",
                        "signal",
                        matched_policy.get("source_url", ""),
                        f"Sender {sender_domain} is not an official employer domain",
                    )
                )

    no_fee = matched_policy and matched_policy.get("no_fee_statement")
    if fee_claim and no_fee:
        evidence.append(
            _ev(
                "ev_fee_policy_conflict",
                1,
                "fee_policy",
                "conflict",
                matched_policy.get("source_url", ""),
                (matched_policy.get("excerpt") or matched_policy.get("normalized_text") or "")[:400],
            )
        )

    if IM_RE.search(text_lower) and matched_policy and (matched_policy.get("forbidden_channels") or "no_im_messaging_interviews" in (matched_policy.get("official_process_steps") or [])):
        evidence.append(
            _ev(
                "ev_im_process_conflict",
                1,
                "im_channel_conflict",
                "conflict",
                matched_policy.get("source_url", ""),
                "Employer policy warns against interviews on WhatsApp/Telegram",
            )
        )
    elif IM_RE.search(text_lower):
        for ch in channels:
            reported = ch.get("reported_channels") or []
            if "whatsapp" in reported or "telegram" in reported:
                evidence.append(
                    _ev(
                        "ev_channel_pattern",
                        1,
                        "reported_channel",
                        "signal",
                        ch.get("source_url", ""),
                        "Government advisory reports job scams via WhatsApp/Telegram",
                    )
                )
                break

    for tac in matched_tactics:
        if tac.get("tactic_id") == "fee_or_deposit_request" and not fee_demand_in_text(text or ""):
            continue
        if tac.get("severity") == "high" and tac.get("tactic_id") not in {"impersonation_big_tech"}:
            evidence.append(
                _ev(
                    f"ev_tac_{tac['tactic_id']}",
                    1 if tac.get("severity") == "high" else 2,
                    tac["tactic_id"],
                    "signal" if not no_fee or tac["tactic_id"] != "fee_or_deposit_request" else "conflict",
                    "",
                    tac.get("user_guidance") or tac.get("display_name", ""),
                )
            )

    if CAPTCHA_TASK_RE.search(text_lower):
        evidence.append(_ev("ev_captcha_task", 1, "captcha_task_scam", "signal", "", "Matches known CAPTCHA/task job scam pattern (India 2024–2025)"))

    if CRYPTO_GIFT_RE.search(text_lower):
        evidence.append(_ev("ev_crypto_gift", 1, "crypto_gift_card", "signal", "", "Payment via crypto or gift cards is a common job scam tactic"))

    if pipeline_profile:
        pipe_evidence = detect_pipeline_conflicts(text, sender_email, pipeline_profile)
        seen_checks = {e.get("check") for e in evidence}
        for pe in pipe_evidence:
            if pe.get("check") not in seen_checks:
                evidence.append(pe)
                seen_checks.add(pe.get("check"))

    if not matched_policy and not pipeline_profile and employer_hint:
        emp_key = _resolve_employer_key(employer_hint, employer_index)
        if emp_key:
            unresolved.append(f"We have registry data for {employer_hint} but no loaded policy snapshot yet.")
        else:
            unresolved.append(f"We could not load an official policy snapshot for {employer_hint}.")

    verdict = compute_verdict(
        evidence,
        fee_claim,
        matched_tactics,
        employer_resolved=bool(matched_policy or pipeline_profile),
    )
    return evidence, unresolved, verdict, matched_tactics


def _policy_from_pipeline(profile: dict[str, Any]) -> dict[str, Any]:
    fraud = profile.get("fraud_policy") or {}
    return {
        "employer_key": profile.get("employer_key"),
        "display_name": profile.get("display_name"),
        "source_url": fraud.get("source_url") or profile.get("india_careers_url", ""),
        "no_fee_statement": profile.get("no_fee_statement", True),
        "official_domains": profile.get("official_domains") or [],
        "forbidden_channels": profile.get("forbidden_channels") or [],
        "official_process_steps": profile.get("official_process_steps") or [],
        "excerpt": (fraud.get("excerpt") or "")[:400],
    }


def _resolve_employer_key(hint: str, employer_index: list[dict[str, Any]]) -> str | None:
    lower = hint.lower()
    for emp in employer_index:
        if lower in emp.get("display_name", "").lower() or lower in emp.get("employer_key", ""):
            return emp.get("employer_key")
        for alias in emp.get("aliases", []):
            if alias.lower() in lower or lower in alias.lower():
                return emp.get("employer_key")
    return None


def _ev(eid: str, tier: int, check: str, outcome: str, source_url: str, excerpt: str) -> dict[str, Any]:
    return {
        "id": eid,
        "tier": tier,
        "check": check,
        "outcome": outcome,
        "sourceUrl": source_url,
        "excerpt": excerpt,
        "fetchedAt": "",
    }


def compute_verdict(
    evidence: list[dict[str, Any]],
    fee_in_text: bool,
    matched_tactics: list[dict[str, Any]] | None = None,
    employer_resolved: bool = False,
) -> str | None:
    t1_conflicts = [e for e in evidence if e.get("tier") == 1 and e.get("outcome") == "conflict"]
    high_tactics = [t for t in (matched_tactics or []) if t.get("severity") == "high"]
    t2_signals = [e for e in evidence if e.get("tier") == 2 and e.get("outcome") == "signal"]

    if t1_conflicts:
        return "high_risk"
    if fee_in_text and (t2_signals or high_tactics):
        return "high_risk"
    if len(high_tactics) >= 2:
        return "high_risk"
    if not evidence:
        if employer_resolved:
            return "no_conflict_found"
        return "unverified"
    if t2_signals and not fee_in_text and len(high_tactics) < 1:
        return "unverified"
    return "no_conflict_found"
