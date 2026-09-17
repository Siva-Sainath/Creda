"""
Creda — Employer Resolver Pipeline (R1–R7).

Given a company name or sender email domain, produce a verified employer profile
— or fail honestly. Every rung writes an evidence record, including the ones
that fail. A user who sees "we could not find an official website for this
company" has learned something real — that is a finding, not an error.

Resolution rungs:
  R1  Cache          EMPLOYER# table, ≤7 days old → instant, zero network
  R2  Wikidata       wbsearchentities → P856 → official domain
  R3  Sender domain  Apex domain corroboration against R2
  R4  Careers page   /careers, /jobs, /work-with-us or homepage link
  R5  ATS detection  Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee
  R6  Policy page    fraud/scam/no-fee/beware links → excerpt
  R7  Give up        employer_unresolved evidence record
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import boto3
import requests

from shared.models import (
    CheckType,
    EmployerProfile,
    EvidenceOutcome,
    EvidenceRecord,
    EvidenceTier,
    ResolverResult,
)

logger = logging.getLogger(__name__)

# S3 client for evidence snapshots
_s3 = boto3.client("s3")
EVIDENCE_BUCKET = os.environ.get("EVIDENCE_BUCKET")

def _save_snapshot(url: str, html: str) -> str | None:
    """Save raw HTML to S3 and return the object key."""
    if not EVIDENCE_BUCKET:
        return None
    try:
        content_bytes = html.encode("utf-8")
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        domain = urlparse(url).netloc.replace(":", "_")
        key = f"snapshots/{domain}/{date_str}/{sha256_hash}.html"
        
        _s3.put_object(
            Bucket=EVIDENCE_BUCKET,
            Key=key,
            Body=content_bytes,
            ContentType="text/html",
            Metadata={"source-url": url}
        )
        return key
    except Exception as e:
        logger.warning(f"Failed to save snapshot for {url}: {e}")
        return None

HTTP_TIMEOUT = 5.0
USER_AGENT = "Creda/1.0 (+https://creda.app)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_domain(domain: str) -> str:
    """Strip www., lowercase, strip trailing slashes/whitespace."""
    domain = domain.lower().strip().rstrip("/")
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _domain_from_url(url: str) -> str:
    """Extract and normalize the domain from a URL."""
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = parsed.netloc or parsed.path.split("/")[0]
        return _normalize_domain(host.split(":")[0])
    except Exception:
        return ""


def _domain_from_email(email: str) -> str:
    """Extract and normalize the domain from an email address."""
    if not email or "@" not in email:
        return ""
    return _normalize_domain(email.split("@")[-1])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ATS patterns: link regex → (platform_name, api_template)
# ---------------------------------------------------------------------------

ATS_PATTERNS: list[tuple[str, str, str]] = [
    (r"boards\.greenhouse\.io/([^/\"'?\s]+)", "greenhouse",
     "https://boards-api.greenhouse.io/v1/boards/{}/jobs"),
    (r"job-boards\.greenhouse\.io/([^/\"'?\s]+)", "greenhouse",
     "https://boards-api.greenhouse.io/v1/boards/{}/jobs"),
    (r"jobs\.lever\.co/([^/\"'?\s]+)", "lever",
     "https://api.lever.co/v0/postings/{}?mode=json"),
    (r"jobs\.ashbyhq\.com/([^/\"'?\s]+)", "ashby",
     "https://api.ashbyhq.com/posting-api/job-board/{}"),
    (r"apply\.workable\.com/([^/\"'?\s]+)", "workable",
     "https://apply.workable.com/api/v1/accounts/{}"),
    (r"careers\.smartrecruiters\.com/([^/\"'?\s]+)", "smartrecruiters",
     "https://api.smartrecruiters.com/v1/companies/{}/postings"),
    (r"([a-z0-9_-]+)\.recruitee\.com", "recruitee",
     "https://{}.recruitee.com/api/offers/"),
]

CAREER_LINK_KEYWORDS = [
    "career", "careers", "jobs", "work with us", "work-with-us",
    "join us", "join-us", "join our team", "we're hiring", "hiring",
]

POLICY_KEYWORDS = [
    "fraud", "scam", "recruitment-fraud", "recruitment fraud",
    "no-fee", "no fee", "beware", "fake", "caution",
    "recruitment-warning", "recruitment warning",
]


class EmployerResolver:
    """
    Resolves an employer profile from a company name or sender email.

    Usage::

        resolver = EmployerResolver()
        result = resolver.resolve(
            company_name="Amazon",
            sender_email="hr@amaz0n-careers.in",
        )
        # result.employer  → EmployerProfile (or None)
        # result.evidence  → list[EvidenceRecord]
        # result.resolved  → bool
    """

    def __init__(self, user_agent: str = USER_AGENT):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    # ------------------------------------------------------------------
    # safe HTTP
    # ------------------------------------------------------------------

    def _get(self, url: str, **kwargs: Any) -> requests.Response | None:
        """GET with timeout and error handling. Returns None on failure."""
        kwargs.setdefault("timeout", HTTP_TIMEOUT)
        try:
            resp = self.session.get(url, **kwargs)
            return resp
        except requests.RequestException as exc:
            logger.warning("GET %s failed: %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # R1 — Cache
    # ------------------------------------------------------------------

    def _r1_cache(
        self, cache_key: str, dynamo_table: Any | None, evidence: list[EvidenceRecord],
    ) -> EmployerProfile | None:
        """Check DynamoDB EMPLOYER# cache, return profile if fresh (≤7 days)."""
        if not dynamo_table or not cache_key:
            return None

        pk = f"EMPLOYER#{cache_key}"
        try:
            item = dynamo_table.get_item(Key={"PK": pk, "SK": "PROFILE"}).get("Item")
            if not item:
                return None

            updated = item.get("resolved_at", "")
            if updated:
                age = datetime.now(timezone.utc) - datetime.fromisoformat(updated)
                if age > timedelta(days=7):
                    return None  # stale

            profile = EmployerProfile(
                company_name=item.get("company_name"),
                query_domain=cache_key,
                official_domain=item.get("official_domain"),
                careers_url=item.get("careers_url"),
                ats_platform=item.get("ats_platform"),
                ats_token=item.get("ats_token"),
                ats_jobs_url=item.get("ats_jobs_url"),
                fee_policy_url=item.get("fee_policy_url"),
                fee_policy_excerpt=item.get("fee_policy_excerpt"),
                resolved_via="cache",
                wikidata_id=item.get("wikidata_id"),
            )
            evidence.append(EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check=CheckType.EMPLOYER_RESOLVED,
                outcome=EvidenceOutcome.CONFIRMED,
                details={"source": "cache", "key": pk},
            ))
            return profile

        except Exception as exc:
            logger.error("DynamoDB cache read failed: %s", exc)
            return None

    def _write_cache(self, cache_key: str, profile: EmployerProfile, dynamo_table: Any | None) -> None:
        """Persist resolved employer to DynamoDB cache with 7-day TTL."""
        if not dynamo_table or not cache_key:
            return
        try:
            item_dict = {k: v for k, v in profile.to_dict().items() if v is not None}
            item_dict["PK"] = f"EMPLOYER#{cache_key}"
            item_dict["SK"] = "PROFILE"
            
            # Add TTL (7 days)
            expire_dt = datetime.now(timezone.utc) + timedelta(days=7)
            item_dict["ttl"] = int(expire_dt.timestamp())
            
            dynamo_table.put_item(Item=item_dict)
        except Exception as exc:
            logger.error("DynamoDB cache write failed: %s", exc)

    # ------------------------------------------------------------------
    # R2 — Wikidata
    # ------------------------------------------------------------------

    def _r2_wikidata(
        self, company_name: str, evidence: list[EvidenceRecord],
    ) -> tuple[str, str | None]:
        """Query Wikidata for official website (P856). Returns (domain, wikidata_id)."""
        if not company_name:
            return "", None

        search_url = (
            "https://www.wikidata.org/w/api.php"
            f"?action=wbsearchentities&search={requests.utils.quote(company_name)}"
            "&language=en&type=item&format=json"
        )
        resp = self._get(search_url)
        if not resp or resp.status_code != 200:
            evidence.append(EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.WIKIDATA_LOOKUP,
                outcome=EvidenceOutcome.UNAVAILABLE,
                source_url=search_url,
                details={"reason": "Wikidata search failed"},
            ))
            return "", None

        try:
            results = resp.json().get("search", [])
            if not results:
                evidence.append(EvidenceRecord(
                    tier=EvidenceTier.T2_TECHNICAL,
                    check=CheckType.WIKIDATA_LOOKUP,
                    outcome=EvidenceOutcome.UNRESOLVED,
                    source_url=search_url,
                    details={"reason": f"No Wikidata entity for '{company_name}'"},
                ))
                return "", None

            entity_id = results[0]["id"]
            entity_url = f"https://www.wikidata.org/wiki/Special:EntityData/{entity_id}.json"
            ent_resp = self._get(entity_url)
            if not ent_resp or ent_resp.status_code != 200:
                evidence.append(EvidenceRecord(
                    tier=EvidenceTier.T2_TECHNICAL,
                    check=CheckType.WIKIDATA_LOOKUP,
                    outcome=EvidenceOutcome.UNAVAILABLE,
                    source_url=entity_url,
                ))
                return "", entity_id

            claims = ent_resp.json().get("entities", {}).get(entity_id, {}).get("claims", {})
            p856 = claims.get("P856", [])
            if not p856:
                evidence.append(EvidenceRecord(
                    tier=EvidenceTier.T2_TECHNICAL,
                    check=CheckType.WIKIDATA_LOOKUP,
                    outcome=EvidenceOutcome.UNRESOLVED,
                    source_url=entity_url,
                    details={"reason": "Entity exists but has no P856 (official website)"},
                ))
                return "", entity_id

            website = p856[0]["mainsnak"]["datavalue"]["value"]
            domain = _domain_from_url(website)
            evidence.append(EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.WIKIDATA_LOOKUP,
                outcome=EvidenceOutcome.CONFIRMED,
                source_url=entity_url,
                excerpt=f"Official website: {website}",
                details={"domain": domain, "wikidata_id": entity_id, "website": website},
            ))
            return domain, entity_id

        except Exception as exc:
            logger.warning("Wikidata parse error: %s", exc)
            evidence.append(EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.WIKIDATA_LOOKUP,
                outcome=EvidenceOutcome.UNAVAILABLE,
                details={"error": str(exc)},
            ))
            return "", None

    # ------------------------------------------------------------------
    # R3 — Sender domain corroboration
    # ------------------------------------------------------------------

    def _r3_sender_domain(
        self,
        sender_email: str | None,
        wikidata_domain: str,
        company_name: str | None,
        evidence: list[EvidenceRecord],
    ) -> str:
        """Cross-check sender apex domain against Wikidata result or homepage."""
        if not sender_email:
            return ""

        sender_domain = _domain_from_email(sender_email)
        if not sender_domain:
            return ""

        if wikidata_domain:
            match = sender_domain == wikidata_domain
            evidence.append(EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check=CheckType.SENDER_DOMAIN_CORROBORATION,
                outcome=EvidenceOutcome.CONFIRMED if match else EvidenceOutcome.CONFLICT,
                details={
                    "sender_domain": sender_domain,
                    "wikidata_domain": wikidata_domain,
                    "match": match,
                },
            ))
            return sender_domain if match else ""

        # Opencode strict security rule: NEVER fetch an unverified sender domain.
        # If Wikidata failed, we DO NOT blindly fetch the sender's apex domain to check for their name.
        # We must rely on deterministic checks instead.

        evidence.append(EvidenceRecord(
            tier=EvidenceTier.T2_TECHNICAL,
            check=CheckType.SENDER_DOMAIN_CORROBORATION,
            outcome=EvidenceOutcome.UNRESOLVED,
            details={"sender_domain": sender_domain, "reason": "Could not corroborate"},
        ))
        return ""

    # ------------------------------------------------------------------
    # R4 — Careers page
    # ------------------------------------------------------------------

    def _r4_careers_page(
        self, domain: str, evidence: list[EvidenceRecord],
    ) -> str:
        """Discover the careers page from the confirmed domain."""
        if not domain:
            return ""

        base = f"https://{domain}"

        # Try well-known paths
        for path in ["/careers", "/jobs", "/work-with-us", "/join-us", "/join", "/careers/"]:
            url = urljoin(base + "/", path.lstrip("/"))
            resp = self._get(url, allow_redirects=True)
            if resp and resp.status_code == 200:
                final_url = resp.url or url
                evidence.append(EvidenceRecord(
                    tier=EvidenceTier.T1_AUTHORITATIVE,
                    check=CheckType.CAREERS_PAGE,
                    outcome=EvidenceOutcome.CONFIRMED,
                    source_url=final_url,
                    details={"method": "well_known_path", "path": path},
                ))
                return final_url

        # Parse homepage for career-related links
        resp = self._get(base, allow_redirects=True)
        if resp and resp.status_code == 200:
            links = re.findall(
                r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                resp.text, re.IGNORECASE | re.DOTALL,
            )
            for href, text in links:
                combined = (href + " " + text).lower()
                if any(kw in combined for kw in CAREER_LINK_KEYWORDS):
                    career_url = urljoin(base + "/", href)
                    # Only follow links on the same domain
                    if _domain_from_url(career_url) == domain:
                        evidence.append(EvidenceRecord(
                            tier=EvidenceTier.T1_AUTHORITATIVE,
                            check=CheckType.CAREERS_PAGE,
                            outcome=EvidenceOutcome.CONFIRMED,
                            source_url=career_url,
                            details={"method": "homepage_link", "link_text": text.strip()[:100]},
                        ))
                        return career_url

        evidence.append(EvidenceRecord(
            tier=EvidenceTier.T1_AUTHORITATIVE,
            check=CheckType.CAREERS_PAGE,
            outcome=EvidenceOutcome.UNAVAILABLE,
            source_url=base,
            details={"reason": "No careers page found"},
        ))
        return ""

    # ------------------------------------------------------------------
    # R5 — ATS detection
    # ------------------------------------------------------------------

    def _r5_ats_detection(
        self, careers_url: str, profile: EmployerProfile, evidence: list[EvidenceRecord],
    ) -> None:
        """Scan careers page HTML for known ATS board links."""
        if not careers_url:
            return

        resp = self._get(careers_url, allow_redirects=True)
        if not resp or resp.status_code != 200:
            evidence.append(EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check=CheckType.ATS_DETECTED,
                outcome=EvidenceOutcome.UNAVAILABLE,
                source_url=careers_url,
                details={"reason": "Could not fetch careers page for ATS scan"},
            ))
            return

        html = resp.text
        for pattern, platform, api_tpl in ATS_PATTERNS:
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                token = m.group(1)
                api_url = api_tpl.format(token)
                profile.ats_platform = platform
                profile.ats_token = token
                profile.ats_jobs_url = api_url
                evidence.append(EvidenceRecord(
                    tier=EvidenceTier.T1_AUTHORITATIVE,
                    check=CheckType.ATS_DETECTED,
                    outcome=EvidenceOutcome.CONFIRMED,
                    source_url=careers_url,
                    details={"platform": platform, "token": token, "api_url": api_url},
                ))
                return

        evidence.append(EvidenceRecord(
            tier=EvidenceTier.T1_AUTHORITATIVE,
            check=CheckType.ATS_DETECTED,
            outcome=EvidenceOutcome.UNRESOLVED,
            source_url=careers_url,
            details={"reason": "No recognised ATS board found on careers page"},
        ))

    # ------------------------------------------------------------------
    # R6 — Policy page
    # ------------------------------------------------------------------

    def _r6_policy_page(
        self, domain: str, careers_url: str, profile: EmployerProfile, evidence: list[EvidenceRecord],
    ) -> None:
        """Scan for recruitment-fraud / no-fee policy pages."""
        pages_to_scan = [f"https://{domain}"]
        if careers_url:
            pages_to_scan.append(careers_url)

        for page_url in pages_to_scan:
            resp = self._get(page_url, allow_redirects=True)
            if not resp or resp.status_code != 200:
                continue

            links = re.findall(
                r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                resp.text, re.IGNORECASE | re.DOTALL,
            )
            for href, text in links:
                combined = (href + " " + text).lower()
                if any(kw in combined for kw in POLICY_KEYWORDS):
                    policy_url = urljoin(page_url, href)
                    pol_resp = self._get(policy_url, allow_redirects=True)
                    if pol_resp and pol_resp.status_code == 200:
                        # Strip HTML tags for excerpt
                        clean = re.sub(r"<[^>]+>", " ", pol_resp.text)
                        clean = re.sub(r"\s+", " ", clean).strip()
                        snippet = clean[:500]
                        if snippet:
                            # Save a snapshot to S3
                            s3_key = _save_snapshot(policy_url, pol_resp.text)

                            profile.fee_policy_url = policy_url
                            profile.fee_policy_excerpt = snippet

                            details = {"excerpt": snippet}
                            if s3_key:
                                details["s3_snapshot_key"] = s3_key

                            evidence.append(EvidenceRecord(
                                tier=EvidenceTier.T1_AUTHORITATIVE,
                                check=CheckType.FEE_POLICY,
                                outcome=EvidenceOutcome.UNAVAILABLE if "scam" in snippet.lower() else EvidenceOutcome.CONFIRMED,
                                source_url=policy_url,
                                excerpt=snippet,
                                details=details,
                            ))
                            return

        evidence.append(EvidenceRecord(
            tier=EvidenceTier.T1_AUTHORITATIVE,
            check=CheckType.FEE_POLICY,
            outcome=EvidenceOutcome.UNAVAILABLE,
            details={"reason": "No recruitment-fraud or fee policy page found"},
        ))

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def resolve(
        self,
        company_name: str | None = None,
        sender_email: str | None = None,
        dynamo_table: Any | None = None,
    ) -> ResolverResult:
        """
        Resolve an employer from a company name and/or sender email.

        Returns a ResolverResult with employer profile, evidence records,
        and whether resolution succeeded.
        """
        evidence: list[EvidenceRecord] = []
        profile = EmployerProfile(
            company_name=company_name,
            query_domain=_domain_from_email(sender_email) if sender_email else None,
        )

        # Build cache key
        cache_key = ""
        if company_name:
            cache_key = company_name.lower().strip()
        elif sender_email:
            cache_key = _domain_from_email(sender_email)

        # R1 — Cache
        cached = self._r1_cache(cache_key, dynamo_table, evidence)
        if cached:
            return ResolverResult(employer=cached, evidence=evidence, resolved=True)

        # R2 — Wikidata
        wikidata_domain, wikidata_id = self._r2_wikidata(company_name, evidence)
        if wikidata_domain:
            profile.official_domain = wikidata_domain
            profile.wikidata_id = wikidata_id
            profile.resolved_via = "wikidata"

        # R3 — Sender domain corroboration
        corroborated = self._r3_sender_domain(sender_email, wikidata_domain, company_name, evidence)
        if corroborated and not profile.official_domain:
            profile.official_domain = corroborated
            profile.resolved_via = "sender_domain"

        # If we still have no domain, give up honestly (R7)
        if not profile.official_domain:
            evidence.append(EvidenceRecord(
                tier=EvidenceTier.T3_DISCOVERY,
                check=CheckType.EMPLOYER_UNRESOLVED,
                outcome=EvidenceOutcome.UNRESOLVED,
                details={
                    "reason": "Could not determine official domain from Wikidata or sender",
                    "question": "What is this company's official website?",
                },
            ))
            return ResolverResult(employer=profile, evidence=evidence, resolved=False)

        domain = profile.official_domain

        # R4 — Careers page
        careers_url = self._r4_careers_page(domain, evidence)
        if careers_url:
            profile.careers_url = careers_url

        # R5 — ATS detection
        self._r5_ats_detection(careers_url, profile, evidence)

        # R6 — Policy page
        self._r6_policy_page(domain, careers_url, profile, evidence)

        # Cache the resolved profile
        self._write_cache(cache_key, profile, dynamo_table)

        # Mark resolved
        evidence.append(EvidenceRecord(
            tier=EvidenceTier.T1_AUTHORITATIVE,
            check=CheckType.EMPLOYER_RESOLVED,
            outcome=EvidenceOutcome.CONFIRMED,
            details={
                "official_domain": domain,
                "resolved_via": profile.resolved_via,
                "has_careers": bool(careers_url),
                "has_ats": bool(profile.ats_platform),
                "has_policy": bool(profile.fee_policy_url),
            },
        ))

        return ResolverResult(employer=profile, evidence=evidence, resolved=True)
