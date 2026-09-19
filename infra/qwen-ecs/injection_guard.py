"""Neutralize common prompt-injection prefixes in user-supplied text (audit original in packet)."""
import re

_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(rules|instructions)"),
    re.compile(r"(?i)you\s+are\s+now\s+dan\b"),
    re.compile(r"(?i)system\s*:\s*"),
    re.compile(r"(?i)mark\s+(this|the\s+offer)\s+(safe|no_conflict_found|clean)"),
    re.compile(r"(?i)verdict\s*:\s*(safe|no_conflict)"),
]


def sanitize_user_text(text: str, max_len: int = 8000) -> tuple[str, list[str]]:
    """Return scrubbed text and list of injection flags for the packet."""
    raw = (text or "")[:max_len]
    flags: list[str] = []
    cleaned = raw
    for pat in _PATTERNS:
        if pat.search(cleaned):
            flags.append(pat.pattern[:40])
            cleaned = pat.sub("[filtered-user-instruction]", cleaned)
    return cleaned.strip(), flags
