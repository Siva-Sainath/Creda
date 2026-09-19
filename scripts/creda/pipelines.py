#!/usr/bin/env python3
"""Build curated India Priority hiring pipeline profiles from YAML + ETL policy rows."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .employers import build_process_profile, employer_lookup, load_registry, resolve_employer_key

ROOT = Path(__file__).resolve().parents[2]
PIPELINES_DIR = ROOT / "data" / "india_priority_pipelines"
PRIORITY_LIST = ROOT / "data" / "india_priority_employers.yaml"


def load_priority_keys() -> list[str]:
    data = yaml.safe_load(PRIORITY_LIST.read_text(encoding="utf-8"))
    return list(data.get("employers", []))


def load_pipeline_yaml(employer_key: str) -> dict[str, Any] | None:
    path = PIPELINES_DIR / f"{employer_key}.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def merge_pipeline_profile(
    curated: dict[str, Any],
    policy_row: dict[str, Any] | None,
    employer: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge hand-authored pipeline YAML with auto-extracted policy signals."""
    key = curated["employer_key"]
    extracted = build_process_profile(policy_row, employer) if policy_row else {}

    no_fee = curated.get("no_fee_statement")
    if no_fee is None:
        no_fee = extracted.get("no_fee_statement", True)

    official_domains = curated.get("official_domains") or extracted.get("official_domains") or []
    if employer:
        official_domains = list(dict.fromkeys(official_domains + employer.get("official_domains", [])))

    forbidden_channels = list(
        dict.fromkeys(
            (curated.get("forbidden_channels") or [])
            + (extracted.get("forbidden_channels") or [])
        )
    )
    forbidden_requests = list(
        dict.fromkeys(
            (curated.get("forbidden_requests") or [])
            + (extracted.get("forbidden_requests") or [])
        )
    )

    fraud = curated.get("fraud_policy") or {}
    if policy_row and not fraud.get("source_url"):
        fraud = {
            "source_url": policy_row.get("source_url"),
            "evidence_id": policy_row.get("evidence_id"),
            "excerpt": (policy_row.get("normalized_text") or "")[:800],
        }

    profile = {
        "profile_id": f"ipep-{key}",
        "employer_key": key,
        "display_name": curated.get("display_name") or (employer or {}).get("display_name", key),
        "scam_target_priority": curated.get("scam_target_priority", "critical"),
        "regions": curated.get("regions", ["india"]),
        "official_domains": official_domains[:15],
        "india_careers_url": curated.get("india_careers_url") or (employer or {}).get("official_careers_urls", [None])[0],
        "global_careers_url": curated.get("global_careers_url"),
        "no_fee_statement": no_fee,
        "forbidden_channels": forbidden_channels,
        "forbidden_requests": forbidden_requests,
        "tracks": curated.get("tracks", []),
        "fraud_policy": fraud,
        "vacancy_source": curated.get("vacancy_source"),
        "sources": curated.get("sources", []),
        "official_process_steps": list(
            dict.fromkeys(
                (extracted.get("official_process_steps") or [])
                + _steps_from_tracks(curated.get("tracks", []))
            )
        ),
        "evidence_tier": "T1",
        "pipeline_version": curated.get("pipeline_version", "ipep-1.0"),
        "last_updated": curated.get("last_updated", "2026-09-17"),
    }
    if policy_row:
        profile["policy_source_id"] = policy_row.get("source_id")
    return profile


def _steps_from_tracks(tracks: list[dict[str, Any]]) -> list[str]:
    steps: set[str] = set()
    for track in tracks:
        for stage in track.get("stages", []):
            sid = stage if isinstance(stage, str) else stage.get("stage_id", "")
            if sid:
                steps.add(sid)
    return sorted(steps)


def build_hiring_pipeline_profiles(
    policies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lookup = employer_lookup()
    by_key = lookup["by_key"]
    policy_by_source = {p["source_id"]: p for p in policies}
    policy_by_employer: dict[str, dict[str, Any]] = {}
    for p in policies:
        key = resolve_employer_key(p.get("source_id", "").split("_")[0], lookup) or resolve_employer_key(
            (p.get("title") or ""), lookup
        )
        if not key:
            for emp_key in load_priority_keys():
                if emp_key in (p.get("source_id") or ""):
                    key = emp_key
                    break
        if key:
            policy_by_employer[key] = p

    profiles = []
    for emp_key in load_priority_keys():
        curated = load_pipeline_yaml(emp_key)
        if not curated:
            continue
        employer = by_key.get(emp_key)
        policy_row = policy_by_employer.get(emp_key)
        if not policy_row and employer:
            sid = (employer.get("policy") or {}).get("source_id")
            if sid:
                policy_row = policy_by_source.get(sid)
        profiles.append(merge_pipeline_profile(curated, policy_row, employer))
    return profiles


def fee_demand_in_text(text: str) -> bool:
    lower = (text or "").lower()
    neg_prefix = re.compile(r"(no|never|don't|do not|without)\s+(?:charge\s+)?(?:any\s+)?$", re.I)
    for match in fee_re.finditer(lower):
        prefix = lower[max(0, match.start() - 30) : match.start()]
        if neg_prefix.search(prefix):
            continue
        token = match.group().lower()
        if token in {"upi", "phonepe", "paytm"} and "pay" not in lower[max(0, match.start() - 20) : match.start()]:
            continue
        return True
    return False


def detect_pipeline_conflicts(
    text: str,
    sender_email: str,
    profile: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return evidence items from hiring pipeline rules."""
    if not profile:
        return []
    evidence: list[dict[str, Any]] = []
    lower = (text or "").lower()
    sender_domain = ""
    if sender_email and "@" in sender_email:
        sender_domain = sender_email.split("@", 1)[1].lower()

    fee_re = re.compile(
        r"\b(fee|fees|deposit|registration|security deposit|training fee|pay (?:inr|rs|₹)|upi|phonepe|paytm)\b",
        re.I,
    )
    im_re = re.compile(r"\b(whatsapp|telegram|whats app)\b", re.I)
    doc_re = re.compile(r"\b(aadhaar|aadhar|pan card|bank account|passport copy)\b", re.I)

    source_url = (profile.get("fraud_policy") or {}).get("source_url") or profile.get("india_careers_url") or ""

    if fee_demand_in_text(lower) and profile.get("no_fee_statement"):
        evidence.append(
            _pipe_ev("pipe_fee_conflict", 1, "conflict", source_url, f"{profile['display_name']} states candidates are never charged fees.")
        )

    for ch in profile.get("forbidden_channels") or []:
        if ch in lower or (ch == "whatsapp" and im_re.search(lower)):
            evidence.append(
                _pipe_ev("pipe_forbidden_channel", 1, "conflict", source_url, f"Official guidance flags {ch} as a scam channel for {profile['display_name']}.")
            )
            break

    if doc_re.search(lower) and "sensitive_documents_early" in (profile.get("forbidden_requests") or []):
        evidence.append(
            _pipe_ev("pipe_early_documents", 1, "signal", source_url, "Sensitive documents requested early; check against official hiring stages.")
        )

    official = [d.lstrip("@") for d in (profile.get("official_domains") or []) if d and "archive" not in d]
    free_mail = {"gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "rediffmail.com", "live.com"}
    if sender_domain in free_mail and official:
        evidence.append(
            _pipe_ev("pipe_free_mail", 2, "signal", source_url, f"Offer from {sender_domain}; {profile['display_name']} typically uses company email domains.")
        )

    for track in profile.get("tracks") or []:
        for forbidden in track.get("forbidden_before_stages") or []:
            if forbidden == "fee_before_interview" and fee_demand_in_text(lower) and "interview" in lower:
                evidence.append(
                    _pipe_ev("pipe_fee_before_process", 1, "conflict", source_url, "Payment demanded before completing official interview stages.")
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
