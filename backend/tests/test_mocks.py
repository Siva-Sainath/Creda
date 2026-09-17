"""
Creda — Mocked tests for Resolver and Checks.
These tests use `responses` to mock out network calls,
addressing Opencode's feedback about missing resolver tests and live networking.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
import responses

from backend.shared.models import EmployerProfile, EvidenceOutcome, EvidenceTier
from backend.worker.resolver import EmployerResolver
from backend.worker.checks import DeterministicChecker


# ---------------------------------------------------------------------------
# Resolver Mocked Tests
# ---------------------------------------------------------------------------

@responses.activate
def test_resolver_wikidata_success():
    """Test R2 Wikidata successful resolution without live network."""
    responses.add(
        responses.GET,
        "https://www.wikidata.org/w/api.php",
        json={"search": [{"id": "Q312"}]},
        status=200,
        match_querystring=False
    )
    responses.add(
        responses.GET,
        "https://www.wikidata.org/wiki/Special:EntityData/Q312.json",
        json={
            "entities": {
                "Q312": {
                    "claims": {
                        "P856": [{"mainsnak": {"datavalue": {"value": "https://www.apple.com/"}}}]
                    }
                }
            }
        },
        status=200
    )

    resolver = EmployerResolver()
    evidence = []
    domain, wiki_id = resolver._r2_wikidata("Apple", evidence)

    assert domain == "apple.com"
    assert wiki_id == "Q312"
    assert any(e.outcome == EvidenceOutcome.CONFIRMED and e.details.get("domain") == "apple.com" for e in evidence)


@responses.activate
def test_resolver_no_untrusted_fetch():
    """Test R3 doesn't blindly fetch sender domains anymore."""
    resolver = EmployerResolver()
    evidence = []
    # R3 Should return empty and UNRESOLVED without trying to do a GET to evil.com
    res = resolver._r3_sender_domain("hr@evil.com", "apple.com", "Apple", evidence)
    
    assert res == ""
    assert any(e.outcome == EvidenceOutcome.CONFLICT for e in evidence)


@responses.activate
def test_resolver_policy_page_extraction():
    """Test R6 correctly extracts the policy excerpt from a known URL."""
    responses.add(
        responses.GET,
        "https://apple.com",
        body='<a href="/fraud-alert">Beware of Recruitment Fraud</a>',
        status=200
    )
    responses.add(
        responses.GET,
        "https://apple.com/fraud-alert",
        body='<html><body><h1>Fraud Warning</h1><p>Apple never asks for money.</p></body></html>',
        status=200
    )

    resolver = EmployerResolver()
    evidence = []
    profile = EmployerProfile(official_domain="apple.com")
    
    resolver._r6_policy_page("apple.com", "", profile, evidence)

    assert profile.fee_policy_url == "https://apple.com/fraud-alert"
    assert "Apple never asks for money." in profile.fee_policy_excerpt


# ---------------------------------------------------------------------------
# Checks Mocked Tests (Replacing live networking)
# ---------------------------------------------------------------------------

@responses.activate
def test_check_domain_age_mocked():
    """Test RDAP check without hitting live servers."""
    responses.add(
        responses.GET,
        "https://rdap.org/domain/recent-scam.com",
        json={"events": [{"eventAction": "registration", "eventDate": "2026-09-01T12:00:00Z"}]},
        status=200
    )

    checker = DeterministicChecker()
    ev = checker.check_domain_age("hr@recent-scam.com")
    
    # 2026-09-01 is < 30 days from 2026-09-17, so it should be a conflict.
    assert ev.outcome == EvidenceOutcome.CONFLICT
    assert ev.details.get("age_days") < 30


@responses.activate
def test_check_mail_posture_cloudflare_fallback():
    """Test Cloudflare DoH fallback for mail posture without live networking."""
    # Note: We simulate ImportError by mocking the exception block, but it's simpler
    # to just test the fallback function directly.
    responses.add(
        responses.GET,
        "https://cloudflare-dns.com/dns-query?name=no-mx.com&type=MX",
        json={"Answer": []}, # Empty answers
        status=200,
        match_querystring=True
    )
    responses.add(
        responses.GET,
        "https://cloudflare-dns.com/dns-query?name=no-mx.com&type=TXT",
        json={"Answer": []}, # Empty answers
        status=200,
        match_querystring=True
    )

    checker = DeterministicChecker()
    ev = checker._mail_posture_doh("no-mx.com")
    
    assert ev.outcome == EvidenceOutcome.CONFLICT
    assert not ev.details.get("has_mx")
    assert not ev.details.get("has_spf")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
