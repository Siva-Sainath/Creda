"""Agent presentation blocks — Qwen chooses component order; server validates shapes."""
from __future__ import annotations

import json
from typing import Any

VERDICT_TITLES = {
    "high_risk": "High risk — do not pay or share documents yet.",
    "no_conflict_found": "No conflict found in the evidence we checked.",
    "unverified": "More evidence is needed before this can be verified.",
}

ALLOWED_BLOCK_TYPES = {
    "verdict_banner",
    "explanation",
    "research_status",
    "evidence_highlights",
    "tactic_highlights",
    "uncertainty",
    "safe_actions",
    "follow_up_questions",
    "conversation",
}

SYSTEM_PROMPT = """Creda explanation agent. Verdict is fixed. Return ONLY minified JSON:
{"blocks":[
 {"type":"verdict_banner","props":{"title":"...","subtitle":"..."}},
 {"type":"explanation","props":{"text":"max 2 sentences"}},
 {"type":"safe_actions","props":{"items":[{"label":"...","detail":"...","tone":"urgent|primary|neutral"}]}},
 {"type":"follow_up_questions","props":{"items":["q1","q2"]}}
]}
Optional: evidence_highlights, tactic_highlights, uncertainty, research_status, conversation.
Never invent evidence. Max 3 follow-ups, 3 safe actions."""


def _clip(text: str, limit: int) -> str:
    return str(text or "")[:limit]


def _jsonable(value: Any) -> Any:
    from decimal import Decimal

    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def packet(item: dict[str, Any]) -> dict[str, Any]:
    raw = _jsonable(
        {
            key: item.get(key, [] if key not in ("verdict", "followUpContext") else item.get(key, ""))
            for key in (
                "verdict",
                "headline",
                "evidence",
                "unresolved",
                "matchedTactics",
                "followUpContext",
                "conversationTurns",
            )
        }
    )
    evidence = []
    for ev in (raw.get("evidence") or [])[:3]:
        if isinstance(ev, dict):
            evidence.append(
                {
                    "check": ev.get("check"),
                    "tier": ev.get("tier") or ev.get("evidence_tier"),
                    "outcome": ev.get("outcome"),
                    "excerpt": _clip(ev.get("excerpt") or ev.get("summary") or "", 160),
                }
            )
    tactics = []
    for tac in (raw.get("matchedTactics") or [])[:2]:
        if isinstance(tac, dict):
            tactics.append(
                {
                    "tactic_id": tac.get("tactic_id") or tac.get("tacticId"),
                    "display_name": _clip(tac.get("display_name") or "", 80),
                    "user_guidance": _clip(tac.get("user_guidance") or "", 120),
                }
            )
    turns = raw.get("conversationTurns") or []
    return {
        "verdict": raw.get("verdict"),
        "headline": _clip(raw.get("headline") or "", 200),
        "evidence": evidence,
        "unresolved": [_clip(u, 120) for u in (raw.get("unresolved") or [])[:3]],
        "matchedTactics": tactics,
        "followUpContext": _clip(raw.get("followUpContext") or "", 400),
        "conversationTurns": turns[-4:] if turns else [],
    }


def _default_headline(verdict: str | None) -> dict[str, str]:
    title = VERDICT_TITLES.get(verdict or "", "Verification complete.")
    return {"title": title, "subtitle": "Creda separated verified evidence from what still needs checking."}


def fallback_blocks(item: dict[str, Any]) -> list[dict[str, Any]]:
    verdict = item.get("verdict") or "unverified"
    evidence = _jsonable(item.get("evidence") or [])
    tactics = _jsonable(item.get("matchedTactics") or [])
    unresolved = _jsonable(item.get("unresolved") or [])
    turns = _jsonable(item.get("conversationTurns") or [])
    headline = _default_headline(verdict)
    explanation = _clip(item.get("headline") or headline["subtitle"], 1800)

    evidence_items = []
    for ev in evidence[:4]:
        if isinstance(ev, dict):
            evidence_items.append(
                {
                    "check": ev.get("check") or "evidence",
                    "text": _clip(ev.get("excerpt") or ev.get("summary") or "", 500),
                    "tier": ev.get("tier") or ev.get("evidence_tier") or 2,
                    "outcome": ev.get("outcome") or "clear",
                }
            )

    tactic_items = []
    for tac in tactics[:3]:
        if isinstance(tac, dict):
            tactic_items.append(
                {
                    "tacticId": tac.get("tactic_id") or tac.get("tacticId") or "pattern",
                    "title": _clip(tac.get("display_name") or tac.get("tactic_id") or "Scam pattern", 120),
                    "guidance": _clip(tac.get("user_guidance") or "", 500),
                }
            )

    safe_items = []
    if verdict == "high_risk":
        safe_items.append(
            {"label": "Do not pay", "detail": "Stop payment until you verify on an official careers channel.", "tone": "urgent"}
        )
    safe_items.append(
        {"label": "Verify on official careers site", "detail": "Compare sender, role, and hiring process with the employer's official jobs page.", "tone": "primary"}
    )

    followups = []
    if unresolved:
        followups.append(f"What can you share about: {unresolved[0]}?")
    followups.extend(["What is the official sender domain?", "What should I do safely before replying?"])

    research = []
    if turns:
        research.append("Re-ran deterministic checks with your follow-up answer")
    research.extend(["Matched employer policies", "Checked scam tactic patterns", "Compared sender and channel signals"])

    blocks = [
        {"type": "verdict_banner", "props": headline},
        {"type": "explanation", "props": {"text": explanation}},
        {"type": "research_status", "props": {"label": "What Creda checked", "items": research[:5]}},
    ]
    if evidence_items:
        blocks.append({"type": "evidence_highlights", "props": {"items": evidence_items}})
    if tactic_items:
        blocks.append({"type": "tactic_highlights", "props": {"items": tactic_items}})
    if unresolved:
        blocks.append({"type": "uncertainty", "props": {"items": [_clip(u, 300) for u in unresolved[:5]]}})
    blocks.append({"type": "safe_actions", "props": {"items": safe_items[:4]}})
    blocks.append({"type": "follow_up_questions", "props": {"items": [_clip(q, 300) for q in followups[:3]]}})
    if turns:
        blocks.append({"type": "conversation", "props": {"turns": turns[-8:]}})
    return blocks


def _sanitize_block(block: Any) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    block_type = block.get("type")
    if block_type not in ALLOWED_BLOCK_TYPES:
        return None
    props = block.get("props") if isinstance(block.get("props"), dict) else {}
    if block_type == "verdict_banner":
        return {"type": block_type, "props": {"title": _clip(props.get("title"), 200), "subtitle": _clip(props.get("subtitle"), 400)}}
    if block_type == "explanation":
        return {"type": block_type, "props": {"text": _clip(props.get("text"), 1800)}}
    if block_type == "research_status":
        items = props.get("items") if isinstance(props.get("items"), list) else []
        return {"type": block_type, "props": {"label": _clip(props.get("label") or "What Creda checked", 120), "items": [_clip(i, 200) for i in items if i][:5]}}
    if block_type in ("evidence_highlights", "tactic_highlights", "uncertainty", "safe_actions", "follow_up_questions"):
        items = props.get("items") if isinstance(props.get("items"), list) else []
        return {"type": block_type, "props": {"items": items[:5] if block_type == "uncertainty" else items[:4]}}
    if block_type == "conversation":
        turns = props.get("turns") if isinstance(props.get("turns"), list) else []
        return {"type": block_type, "props": {"turns": turns[-8:]}}
    return None


def parse_model(raw: str, item: dict[str, Any]) -> dict[str, Any]:
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Model did not return JSON")
    value = json.loads(raw[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Model response is not an object")

    blocks = []
    for block in value.get("blocks") or []:
        cleaned = _sanitize_block(block)
        if cleaned:
            blocks.append(cleaned)

    required = {b["type"] for b in blocks}
    fallback = fallback_blocks(item)
    fallback_map = {b["type"]: b for b in fallback}
    for needed in ("verdict_banner", "explanation", "safe_actions"):
        if needed not in required and needed in fallback_map:
            blocks.insert(0 if needed == "verdict_banner" else len(blocks), fallback_map[needed])

    if not blocks:
        blocks = fallback

    summary = next((b["props"].get("text", "") for b in blocks if b["type"] == "explanation"), "")
    followups = next((b["props"].get("items", []) for b in blocks if b["type"] == "follow_up_questions"), [])

    return {
        "version": 2,
        "blocks": blocks,
        "headline": next((b["props"] for b in blocks if b["type"] == "verdict_banner"), _default_headline(item.get("verdict"))),
        "explanation": {"text": summary},
        "followUpQuestions": followups,
    }
