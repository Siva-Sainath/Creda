"""
Creda — shared data models.

Every evidence record, employer profile, and verdict flows through these types.
The model never decides the verdict — computeVerdict() in verdict.py does.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EvidenceTier(int, Enum):
    """What kind of source produced this evidence."""
    T1_AUTHORITATIVE = 1   # employer's own site, ATS feed, govt registry, I4C/CERT-In
    T2_TECHNICAL = 2       # RDAP, DNS, lookalike distance, Wikidata, URL reputation
    T3_DISCOVERY = 3       # Reddit, forums, news, user reports — never sets a verdict


class EvidenceOutcome(str, Enum):
    """What the check found."""
    CONFLICT = "conflict"           # evidence contradicts the offer
    CONFIRMED = "confirmed"         # evidence supports the offer
    UNAVAILABLE = "unavailable"     # source blocked, timed out, or missing
    UNRESOLVED = "unresolved"       # could not determine either way


class Verdict(str, Enum):
    """The three words that are the product."""
    HIGH_RISK = "high_risk"
    UNVERIFIED = "unverified"
    NO_CONFLICT_FOUND = "no_conflict_found"


class CaseStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    NEEDS_EVIDENCE = "needs_evidence"
    COULD_NOT_COMPLETE = "could_not_complete"


class CheckType(str, Enum):
    """Known deterministic check names."""
    DOMAIN_MATCH = "domain_match"
    FREE_MAILBOX = "free_mailbox"
    LOOKALIKE_DOMAIN = "lookalike_domain"
    DOMAIN_AGE = "domain_age"
    MAIL_POSTURE = "mail_posture"
    PAYMENT_DEMAND = "payment_demand"
    LINK_DESTINATION = "link_destination"
    URL_REPUTATION = "url_reputation"
    FEE_POLICY = "fee_policy"
    VACANCY_MATCH = "vacancy_match"
    EMPLOYER_RESOLVED = "employer_resolved"
    EMPLOYER_UNRESOLVED = "employer_unresolved"
    CAREERS_PAGE = "careers_page"
    ATS_DETECTED = "ats_detected"
    SENDER_DOMAIN_CORROBORATION = "sender_domain_corroboration"
    WIKIDATA_LOOKUP = "wikidata_lookup"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

def _new_id(prefix: str = "ev") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvidenceRecord:
    """One piece of evidence produced by a check or resolver rung."""
    id: str = field(default_factory=lambda: _new_id("ev"))
    tier: EvidenceTier = EvidenceTier.T2_TECHNICAL
    check: str = ""                       # CheckType value or free string
    outcome: EvidenceOutcome = EvidenceOutcome.UNRESOLVED
    source_url: Optional[str] = None
    excerpt: Optional[str] = None
    fetched_at: str = field(default_factory=_now_iso)
    s3_key: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier.value,
            "check": self.check,
            "outcome": self.outcome.value,
            "sourceUrl": self.source_url,
            "excerpt": self.excerpt,
            "fetchedAt": self.fetched_at,
            "s3Key": self.s3_key,
            "details": self.details,
        }


@dataclass
class EmployerProfile:
    """Resolved employer identity — cached in EMPLOYER#{domain} table."""
    company_name: Optional[str] = None
    query_domain: Optional[str] = None          # what the user/sender gave us
    official_domain: Optional[str] = None       # confirmed via Wikidata or homepage
    careers_url: Optional[str] = None
    ats_platform: Optional[str] = None          # "greenhouse", "lever", etc.
    ats_token: Optional[str] = None             # board token for ATS API
    ats_jobs_url: Optional[str] = None          # direct API endpoint for vacancies
    fee_policy_url: Optional[str] = None
    fee_policy_excerpt: Optional[str] = None
    resolved_via: Optional[str] = None          # "wikidata", "sender_domain", "cache"
    wikidata_id: Optional[str] = None
    resolved_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Claim:
    """A structured claim extracted from the offer text."""
    id: str = field(default_factory=lambda: _new_id("cl"))
    type: str = ""                 # payment_demand, employer_name, job_title, urgency, etc.
    value: str = ""
    quote: Optional[str] = None    # verbatim text from the offer

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "value": self.value,
            "quote": self.quote,
        }


@dataclass
class ResolverResult:
    """Output of the employer resolver pipeline."""
    employer: Optional[EmployerProfile] = None
    evidence: list[EvidenceRecord] = field(default_factory=list)
    resolved: bool = False


@dataclass
class ChecksResult:
    """Output of the deterministic checks pipeline."""
    evidence: list[EvidenceRecord] = field(default_factory=list)
    claims_extracted: list[Claim] = field(default_factory=list)


@dataclass
class CaseInput:
    """What the candidate submits."""
    text: str = ""
    sender_email: Optional[str] = None
    links: list[str] = field(default_factory=list)
    employer_hint: Optional[str] = None
    locale: str = "en-IN"
