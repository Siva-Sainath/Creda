"""Employer registry load, fetch orchestration, and process profile extraction."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data" / "employer_registry.yaml"
MANUAL_DIR = ROOT / "data" / "manual_snapshots"

FREE_MAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com",
    "yahoo.co.uk", "rediffmail.com", "proton.me", "protonmail.com", "live.com",
}

PROCESS_STEP_RULES: list[tuple[str, str]] = [
    ("no_fee_to_candidates", r"\b(no fee|never charge|do not ask for money|does not charge|never request money|no registration fee|security deposit)\b"),
    ("formal_interview_required", r"\b(interview|screening|assessment)\b"),
    ("apply_via_official_careers_site", r"\b(official careers|careers site|careers page|careers\.)\b"),
    ("official_email_domain_expected", r"\b(@[a-z0-9.-]+\.(?:com|in)|official email|company domain|email address ending)\b"),
    ("free_mailbox_is_red_flag", r"\b(gmail|yahoo|hotmail|outlook|free email|free webmail|rediff)\b"),
    ("no_im_messaging_interviews", r"\b(whatsapp|telegram|instant messaging|messaging app)\b"),
    ("no_bank_details_before_offer", r"\b(bank account|banking information|aadhaar|pan card|credit card|tax form)\b"),
    ("verify_offer_letter_portal", r"\b(offer letter|offer verification|joining\.|verify.*offer)\b"),
]


def load_registry() -> dict[str, Any]:
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))


def employer_lookup(registry: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    registry = registry or load_registry()
    by_key: dict[str, dict[str, Any]] = {}
    alias_map: dict[str, str] = {}
    for emp in registry.get("employers", []):
        key = emp["employer_key"]
        by_key[key] = emp
        alias_map[key.lower()] = key
        for alias in emp.get("aliases", []):
            alias_map[alias.lower()] = key
        alias_map[emp["display_name"].lower()] = key
    return {"by_key": by_key, "alias_map": alias_map}


def resolve_employer_key(hint: str, lookup: dict[str, Any] | None = None) -> str | None:
    if not hint:
        return None
    lookup = lookup or employer_lookup()
    alias_map = lookup["alias_map"]
    lower = hint.lower().strip()
    if lower in alias_map:
        return alias_map[lower]
    for alias, key in alias_map.items():
        if alias in lower or lower in alias:
            return key
    return None


def build_process_profile(policy_row: dict[str, Any], employer: dict[str, Any] | None = None) -> dict[str, Any]:
    text = policy_row.get("normalized_text") or ""
    lower = text.lower()
    claims = {}
    try:
        claims = json.loads(policy_row.get("extracted_claims") or "{}")
    except Exception:
        claims = {}

    steps = [step for step, pat in PROCESS_STEP_RULES if re.search(pat, lower, re.I)]
    no_fee = bool(claims.get("no_fee_statement")) or "no_fee_to_candidates" in steps or re.search(
        r"\b(don't charge|do not charge|never charge|no fee|does not charge|never request money)\b", lower, re.I
    )

    official_domains = list(employer.get("official_domains", [])) if employer else []
    for d in claims.get("sender_domains") or []:
        if d and d not in FREE_MAIL_DOMAINS and d not in official_domains:
            official_domains.append(d)

    forbidden_channels = []
    if re.search(r"\b(whatsapp|telegram|instant messaging|messaging app)\b", lower, re.I):
        forbidden_channels.extend(["whatsapp", "telegram"])

    return {
        "employer_key": (employer or {}).get("employer_key") or policy_row.get("source_id", "").split("_")[0],
        "display_name": (employer or {}).get("display_name") or policy_row.get("title", ""),
        "company_tier": (employer or {}).get("company_tier", "unknown"),
        "regions": (employer or {}).get("regions", []),
        "scam_target_priority": (employer or {}).get("scam_target_priority", "medium"),
        "source_id": policy_row.get("source_id"),
        "source_url": policy_row.get("source_url"),
        "evidence_id": policy_row.get("evidence_id"),
        "no_fee_statement": no_fee,
        "official_domains": official_domains[:12],
        "official_careers_urls": (employer or {}).get("official_careers_urls", []),
        "official_process_steps": steps,
        "forbidden_channels": sorted(set(forbidden_channels)),
        "forbidden_requests": _forbidden_requests(lower, claims),
        "evidence_tier": policy_row.get("evidence_tier", "T1"),
    }


def _forbidden_requests(lower: str, claims: dict[str, Any]) -> list[str]:
    reqs = []
    if claims.get("fees_requested") or re.search(r"\b(fee|deposit|payment|money)\b", lower):
        reqs.append("fee_or_deposit")
    if claims.get("document_requests") or re.search(r"\b(bank account|aadhaar|pan card)\b", lower):
        reqs.append("sensitive_documents_early")
    if re.search(r"\b(whatsapp|telegram)\b", lower):
        reqs.append("im_only_interview")
    return reqs


def build_employer_index(registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = registry or load_registry()
    rows = []
    for emp in registry.get("employers", []):
        rows.append(
            {
                "employer_key": emp["employer_key"],
                "display_name": emp["display_name"],
                "company_tier": emp.get("company_tier"),
                "regions": emp.get("regions", []),
                "scam_target_priority": emp.get("scam_target_priority", "medium"),
                "official_domains": emp.get("official_domains", []),
                "official_careers_urls": emp.get("official_careers_urls", []),
                "aliases": emp.get("aliases", []),
                "has_policy": bool(emp.get("policy")),
                "has_ats": bool(emp.get("ats")),
                "policy_source_id": (emp.get("policy") or {}).get("source_id"),
                "ats_source_id": (emp.get("ats") or {}).get("source_id"),
            }
        )
    return rows
