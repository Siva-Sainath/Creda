"""Scam tactic registry — load, compile, match, and dynamic updates."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
TACTICS_PATH = ROOT / "data" / "scam_tactics_registry.yaml"


def load_tactics_registry() -> dict[str, Any]:
    return yaml.safe_load(TACTICS_PATH.read_text(encoding="utf-8"))


def compile_tactics(registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = registry or load_tactics_registry()
    compiled = []
    for tac in registry.get("tactics", []):
        if not tac.get("active", True):
            continue
        patterns = []
        for raw in tac.get("detection_regex", []):
            try:
                patterns.append(re.compile(raw, re.I))
            except re.error:
                continue
        compiled.append({**tac, "_patterns": patterns})
    return compiled


def match_tactics(text: str, sender_email: str = "", compiled: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    compiled = compiled or compile_tactics()
    haystack = f"{text}\n{sender_email}".strip()
    if not haystack:
        return []
    matched = []
    for tac in compiled:
        for pat in tac["_patterns"]:
            m = pat.search(haystack)
            if not m:
                continue
            matched.append(
                {
                    "tactic_id": tac["tactic_id"],
                    "display_name": tac["display_name"],
                    "severity": tac.get("severity", "medium"),
                    "category": tac.get("category", "unknown"),
                    "regions": tac.get("regions", []),
                    "user_guidance": tac.get("user_guidance", ""),
                    "matched_span": m.group(0)[:120],
                    "source_ids": tac.get("source_ids", []),
                    "last_updated": tac.get("last_updated"),
                }
            )
            break
    return matched


def tactics_to_jsonl_rows(registry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = registry or load_tactics_registry()
    rows = []
    for tac in registry.get("tactics", []):
        rows.append({k: v for k, v in tac.items() if not k.startswith("_")})
    return rows


def add_tactic(
    tactic_id: str,
    display_name: str,
    detection_regex: list[str],
    user_guidance: str,
    *,
    severity: str = "medium",
    category: str = "unknown",
    regions: list[str] | None = None,
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    registry = load_tactics_registry()
    tactics = registry.setdefault("tactics", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = next((t for t in tactics if t.get("tactic_id") == tactic_id), None)
    entry = {
        "tactic_id": tactic_id,
        "display_name": display_name,
        "severity": severity,
        "regions": regions or ["global"],
        "category": category,
        "detection_regex": detection_regex,
        "user_guidance": user_guidance,
        "first_seen": today,
        "last_updated": today,
        "source_ids": source_ids or ["user_report"],
        "active": True,
    }
    if existing:
        existing.update(entry)
    else:
        tactics.append(entry)
    registry["updated_at"] = today
    TACTICS_PATH.write_text(yaml.dump(registry, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return entry
