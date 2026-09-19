from __future__ import annotations

import re
from typing import Any

FEE_RE = re.compile(
    r"\b(fee|fees|deposit|registration|security deposit|training fee|pay (?:inr|rs|₹)|upi|phonepe|paytm)\b",
    re.I,
)
NEG_FEE_PREFIX = re.compile(r"(no|never|don't|do not|without)\s+(?:charge\s+)?(?:any\s+)?$", re.I)


def fee_demand_in_text(text: str) -> bool:
    """True when text likely demands payment, not when denying fees (e.g. 'no fees')."""
    lower = (text or "").lower()
    for match in FEE_RE.finditer(lower):
        prefix = lower[max(0, match.start() - 30) : match.start()]
        if NEG_FEE_PREFIX.search(prefix):
            continue
        token = match.group().lower()
        if token in {"upi", "phonepe", "paytm"} and "pay" not in lower[max(0, match.start() - 20) : match.start()]:
            continue
        return True
    return False
IM_RE = re.compile(r"\b(whatsapp|telegram|whats app)\b", re.I)
DOC_RE = re.compile(r"\b(aadhaar|aadhar|pan card|bank account|passport copy)\b", re.I)
FREE_MAIL = {"gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "rediffmail.com", "live.com"}


def resolve_hiring_pipeline(
    profiles: list[dict[str, Any]],
    employer_hint: str,
    employer_index: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    hint = (employer_hint or "").lower().strip()
    if not hint:
        return None

    for profile in profiles:
        key = (profile.get("employer_key") or "").lower()
        name = (profile.get("display_name") or "").lower()
        if key and (key in hint or hint in key):
            return profile
        if name and (name in hint or hint in name):
            return profile

    if employer_index:
        for emp in employer_index:
            emp_key = (emp.get("employer_key") or "").lower()
            display = (emp.get("display_name") or "").lower()
            if hint in emp_key or hint in display:
                for profile in profiles:
                    if profile.get("employer_key") == emp.get("employer_key"):
                        return profile
            for alias in emp.get("aliases") or []:
                alias_lower = alias.lower()
                if alias_lower in hint or hint in alias_lower:
                    for profile in profiles:
                        if profile.get("employer_key") == emp.get("employer_key"):
                            return profile
    return None


def detect_pipeline_conflicts(
    text: str,
    sender_email: str,
    profile: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not profile:
        return []

    evidence: list[dict[str, Any]] = []
    lower = (text or "").lower()
    sender_domain = ""
    if sender_email and "@" in sender_email:
        sender_domain = sender_email.split("@", 1)[1].lower()

    source_url = (profile.get("fraud_policy") or {}).get("source_url") or profile.get("india_careers_url") or ""

    if fee_demand_in_text(lower) and profile.get("no_fee_statement"):
        evidence.append(
            _pipe_ev(
                "pipe_fee_conflict",
                1,
                "conflict",
                source_url,
                f"{profile['display_name']} states candidates are never charged fees.",
            )
        )

    for ch in profile.get("forbidden_channels") or []:
        if ch in lower or (ch == "whatsapp" and IM_RE.search(lower)):
            evidence.append(
                _pipe_ev(
                    "pipe_forbidden_channel",
                    1,
                    "conflict",
                    source_url,
                    f"Official guidance flags {ch} as a scam channel for {profile['display_name']}.",
                )
            )
            break

    if doc_re := DOC_RE.search(lower):
        if "sensitive_documents_early" in (profile.get("forbidden_requests") or []):
            evidence.append(
                _pipe_ev(
                    "pipe_early_documents",
                    1,
                    "signal",
                    source_url,
                    "Sensitive documents requested early; check against official hiring stages.",
                )
            )

    if sender_domain in FREE_MAIL and profile.get("official_domains"):
        evidence.append(
            _pipe_ev(
                "pipe_free_mail",
                2,
                "signal",
                source_url,
                f"Offer from {sender_domain}; {profile['display_name']} typically uses company email domains.",
            )
        )

    for track in profile.get("tracks") or []:
        for forbidden in track.get("forbidden_before_stages") or []:
            if forbidden == "fee_before_interview" and fee_demand_in_text(lower) and "interview" in lower:
                evidence.append(
                    _pipe_ev(
                        "pipe_fee_before_process",
                        1,
                        "conflict",
                        source_url,
                        "Payment demanded before completing official interview stages.",
                    )
                )

    return evidence


def _pipe_ev(eid: str, tier: int, outcome: str, source_url: str, excerpt: str) -> dict[str, Any]:
    return {
        "id": eid,
        "tier": tier,
        "check": eid.replace("pipe_", ""),
        "outcome": outcome,
        "sourceUrl": source_url,
        "excerpt": excerpt,
        "fetchedAt": "",
        "pipeline": True,
    }
