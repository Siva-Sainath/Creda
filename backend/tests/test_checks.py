"""
Creda — deterministic checks unit tests.

Tests the check functions against known inputs without making
real network calls (except where noted for RDAP/DNS).
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from backend.shared.models import (
    EmployerProfile,
    EvidenceOutcome,
    EvidenceTier,
)
from backend.worker.checks import (
    DeterministicChecker,
    extract_apex_domain,
    extract_email_domain,
    extract_urls_from_text,
    levenshtein_distance,
)


@pytest.fixture
def checker():
    return DeterministicChecker()


@pytest.fixture
def amazon_profile():
    return EmployerProfile(
        company_name="Amazon",
        official_domain="amazon.com",
        careers_url="https://www.amazon.jobs",
    )


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_extract_apex_from_email(self):
        assert extract_apex_domain("hr@amazon.com") == "amazon.com"

    def test_extract_apex_from_url(self):
        assert extract_apex_domain("https://www.boards.greenhouse.io/test") == "greenhouse.io"

    def test_extract_apex_two_part_tld(self):
        assert extract_apex_domain("hr@careers.amazon.co.in") == "amazon.co.in"

    def test_extract_apex_empty(self):
        assert extract_apex_domain("") is None

    def test_email_domain(self):
        assert extract_email_domain("hr@mail.amazon.com") == "mail.amazon.com"

    def test_urls_from_text(self):
        text = "Apply at https://jobs.amazon.com/apply and https://bit.ly/abc123"
        urls = extract_urls_from_text(text)
        assert len(urls) == 2
        assert "https://jobs.amazon.com/apply" in urls

    def test_levenshtein_same(self):
        assert levenshtein_distance("amazon", "amazon") == 0

    def test_levenshtein_one_off(self):
        assert levenshtein_distance("amazon", "amaz0n") == 1

    def test_levenshtein_different(self):
        assert levenshtein_distance("amazon", "google") == 6


# ---------------------------------------------------------------------------
# Domain match
# ---------------------------------------------------------------------------

class TestDomainMatch:

    def test_sender_matches_official(self, checker, amazon_profile):
        ev = checker.check_domain_match("hr@amazon.com", amazon_profile)
        assert ev.outcome == EvidenceOutcome.CONFIRMED

    def test_sender_is_ats_domain(self, checker, amazon_profile):
        ev = checker.check_domain_match("noreply@greenhouse.io", amazon_profile)
        assert ev.outcome == EvidenceOutcome.CONFIRMED
        assert ev.details["is_ats"] is True

    def test_sender_mismatches_official(self, checker, amazon_profile):
        ev = checker.check_domain_match("hr@amaz0n-careers.in", amazon_profile)
        assert ev.outcome == EvidenceOutcome.CONFLICT

    def test_no_official_domain(self, checker):
        ev = checker.check_domain_match("hr@company.com", EmployerProfile())
        assert ev.outcome == EvidenceOutcome.UNRESOLVED

    def test_no_sender_email(self, checker, amazon_profile):
        ev = checker.check_domain_match(None, amazon_profile)
        assert ev.outcome == EvidenceOutcome.UNRESOLVED


# ---------------------------------------------------------------------------
# Free mailbox
# ---------------------------------------------------------------------------

class TestFreeMailbox:

    def test_gmail_with_fee_is_conflict(self, checker):
        ev = checker.check_free_mailbox("hr@gmail.com", "Please pay the registration fee of Rs 3500")
        assert ev.outcome == EvidenceOutcome.CONFLICT

    def test_gmail_no_fee_is_unresolved(self, checker):
        ev = checker.check_free_mailbox("hr@gmail.com", "Congratulations, you are selected")
        assert ev.outcome == EvidenceOutcome.UNRESOLVED

    def test_corporate_email_is_confirmed(self, checker):
        ev = checker.check_free_mailbox("hr@amazon.com", "Please pay the fee")
        assert ev.outcome == EvidenceOutcome.CONFIRMED


# ---------------------------------------------------------------------------
# Lookalike domain
# ---------------------------------------------------------------------------

class TestLookalikeDomain:

    def test_amaz0n_is_lookalike(self, checker, amazon_profile):
        ev = checker.check_lookalike_domain("hr@amaz0n.com", amazon_profile)
        assert ev.outcome == EvidenceOutcome.CONFLICT
        assert ev.details["distance"] <= 3

    def test_amazon_careers_suffix(self, checker, amazon_profile):
        ev = checker.check_lookalike_domain("hr@amazon-careers.com", amazon_profile)
        assert ev.outcome == EvidenceOutcome.CONFLICT
        assert ev.details["has_scam_suffix"] is True

    def test_exact_match_is_not_lookalike(self, checker, amazon_profile):
        ev = checker.check_lookalike_domain("hr@amazon.com", amazon_profile)
        assert ev.outcome == EvidenceOutcome.CONFIRMED

    def test_completely_different_domain(self, checker, amazon_profile):
        ev = checker.check_lookalike_domain("hr@totallyunrelated.org", amazon_profile)
        assert ev.outcome == EvidenceOutcome.UNRESOLVED


# ---------------------------------------------------------------------------
# Payment demand extraction
# ---------------------------------------------------------------------------

class TestPaymentDemand:

    def test_upi_id_detected(self, checker):
        text = "Pay Rs 3500 to recruiter@paytm immediately"
        ev = checker.check_payment_demand(text)
        assert ev.outcome == EvidenceOutcome.CONFIRMED
        assert "upi_id" in ev.details

    def test_bank_account_detected(self, checker):
        text = "Transfer to Account 123456789012 IFSC: HDFC0001234"
        ev = checker.check_payment_demand(text)
        assert ev.outcome == EvidenceOutcome.CONFIRMED
        assert "bank_account" in ev.details
        assert "ifsc" in ev.details

    def test_amount_in_rupees(self, checker):
        text = "Registration fee: ₹3,500 must be paid before joining"
        ev = checker.check_payment_demand(text)
        assert ev.outcome == EvidenceOutcome.CONFIRMED
        assert "amount" in ev.details
        assert "3500" in ev.details["amount"]

    def test_no_payment_found(self, checker):
        text = "Congratulations! You have been selected for the role of SDE-1."
        ev = checker.check_payment_demand(text)
        assert ev.outcome == EvidenceOutcome.UNRESOLVED

    def test_gift_card_detected(self, checker):
        text = "Please purchase an Amazon Pay gift card worth Rs 5000"
        ev = checker.check_payment_demand(text)
        assert ev.outcome == EvidenceOutcome.CONFIRMED
        assert "gift_card" in ev.details


# ---------------------------------------------------------------------------
# Link destinations
# ---------------------------------------------------------------------------

class TestLinkDestinations:

    def test_shortener_is_conflict(self, checker, amazon_profile):
        ev = checker.check_link_destinations(
            "Apply here: https://bit.ly/fake-amazon-job", [], amazon_profile,
        )
        assert ev.outcome == EvidenceOutcome.CONFLICT

    def test_ip_address_is_conflict(self, checker, amazon_profile):
        ev = checker.check_link_destinations(
            "Form: http://192.168.1.1/apply", [], amazon_profile,
        )
        assert ev.outcome == EvidenceOutcome.CONFLICT

    def test_official_link_is_confirmed(self, checker, amazon_profile):
        ev = checker.check_link_destinations(
            "Apply at https://amazon.com/jobs/123", [], amazon_profile,
        )
        assert ev.outcome == EvidenceOutcome.CONFIRMED

    def test_no_links_is_unresolved(self, checker, amazon_profile):
        ev = checker.check_link_destinations("No links here", [], amazon_profile)
        assert ev.outcome == EvidenceOutcome.UNRESOLVED


# ---------------------------------------------------------------------------
# run_all_checks integration
# ---------------------------------------------------------------------------

class TestRunAllChecks:

    def test_scam_offer_produces_multiple_evidence_records(self, checker, amazon_profile):
        result = checker.run_all_checks(
            offer_text="Pay ₹3,500 registration fee to recruiter@paytm. Apply: https://bit.ly/amzn-job",
            sender_email="hr@amaz0n-careers.in",
            links=[],
            employer=amazon_profile,
        )
        assert len(result.evidence) == 7  # one per check
        # At least some should be conflicts
        conflicts = [e for e in result.evidence if e.outcome == EvidenceOutcome.CONFLICT]
        assert len(conflicts) >= 2  # domain match + lookalike at minimum

    def test_legitimate_offer_has_no_conflicts(self, checker, amazon_profile):
        result = checker.run_all_checks(
            offer_text="We are pleased to offer you the SDE-1 position. Please visit https://amazon.com/onboard",
            sender_email="hr@amazon.com",
            links=[],
            employer=amazon_profile,
        )
        conflicts = [e for e in result.evidence if e.outcome == EvidenceOutcome.CONFLICT]
        assert len(conflicts) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
