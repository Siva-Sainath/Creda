"""
Creda — verdict computation tests.

The brief says: "Unit-test that function with a fabricated 'high risk'
model output and zero evidence records — it must return unverified.
That test is worth showing a judge."
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from backend.shared.models import (
    EvidenceOutcome,
    EvidenceRecord,
    EvidenceTier,
    Verdict,
)
from backend.shared.verdict import compute_verdict


# ---------------------------------------------------------------------------
# THE test: fabricated model says high_risk, zero evidence → unverified
# ---------------------------------------------------------------------------

class TestModelCannotOverrideVerdict:
    """The model never decides. These tests prove it."""

    def test_model_says_high_risk_but_no_evidence(self):
        """Fabricated model output claiming high risk + zero evidence = unverified."""
        result = compute_verdict(
            evidence=[],
            model_verdict_candidate="high_risk",
        )
        assert result == Verdict.UNVERIFIED

    def test_model_says_high_risk_but_only_t3_conflicts(self):
        """T3 (discovery) conflicts can NEVER move the verdict."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T3_DISCOVERY,
                check="reddit_report",
                outcome=EvidenceOutcome.CONFLICT,
                source_url="https://reddit.com/r/jobs/example",
                excerpt="Someone said this is a scam",
            ),
            EvidenceRecord(
                tier=EvidenceTier.T3_DISCOVERY,
                check="news_report",
                outcome=EvidenceOutcome.CONFLICT,
                source_url="https://news.example.com/article",
                excerpt="Reports of fraud",
            ),
        ]
        result = compute_verdict(evidence, model_verdict_candidate="high_risk")
        assert result == Verdict.UNVERIFIED


# ---------------------------------------------------------------------------
# HIGH RISK: T1 conflict
# ---------------------------------------------------------------------------

class TestHighRisk:
    """High risk requires real evidence, never just suspicion."""

    def test_single_t1_conflict_is_high_risk(self):
        """One T1 conflict (e.g. fee policy contradiction) → high risk."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="fee_policy",
                outcome=EvidenceOutcome.CONFLICT,
                source_url="https://amazon.jobs/fraud-alert",
                excerpt="Amazon never charges fees for recruitment",
            ),
        ]
        assert compute_verdict(evidence) == Verdict.HIGH_RISK

    def test_t1_conflict_plus_t2_confirmed_still_high_risk(self):
        """One T1 conflict overrides any number of T2 confirmations."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="fee_policy",
                outcome=EvidenceOutcome.CONFLICT,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="domain_age",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="mail_posture",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
        ]
        assert compute_verdict(evidence) == Verdict.HIGH_RISK

    def test_two_t2_conflicts_plus_payment_demand_is_high_risk(self):
        """Two independent T2 signals + payment demand → high risk."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="lookalike_domain",
                outcome=EvidenceOutcome.CONFLICT,
                details={"distance": 2, "official": "amazon.com", "sender": "amaz0n-careers.in"},
            ),
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="domain_age",
                outcome=EvidenceOutcome.CONFLICT,
                details={"age_days": 9},
            ),
            EvidenceRecord(
                check="payment_demand",
                outcome=EvidenceOutcome.CONFIRMED,
                details={"amount": "3500", "upi_id": "recruiter@paytm"},
            ),
        ]
        assert compute_verdict(evidence) == Verdict.HIGH_RISK

    def test_single_t2_conflict_plus_payment_is_NOT_high_risk(self):
        """Only ONE T2 conflict + payment → unverified, not high risk."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="domain_age",
                outcome=EvidenceOutcome.CONFLICT,
                details={"age_days": 15},
            ),
            EvidenceRecord(
                check="payment_demand",
                outcome=EvidenceOutcome.CONFIRMED,
                details={"amount": "3500"},
            ),
        ]
        assert compute_verdict(evidence) == Verdict.UNVERIFIED


# ---------------------------------------------------------------------------
# NO CONFLICT FOUND
# ---------------------------------------------------------------------------

class TestNoConflictFound:
    """No conflict found requires positive evidence, not absence."""

    def test_employer_confirmed_and_vacancy_matched_and_zero_conflicts(self):
        """All checks pass → no conflict found."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="employer_resolved",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="domain_match",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="vacancy_match",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="domain_age",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="mail_posture",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
        ]
        assert compute_verdict(evidence) == Verdict.NO_CONFLICT_FOUND

    def test_missing_vacancy_match_means_unverified(self):
        """Employer confirmed but no vacancy match → unverified."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="domain_match",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="domain_age",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
        ]
        assert compute_verdict(evidence) == Verdict.UNVERIFIED

    def test_any_unavailable_check_prevents_no_conflict(self):
        """A source we couldn't reach = we don't know = unverified."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="domain_match",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="vacancy_match",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="fee_policy",
                outcome=EvidenceOutcome.UNAVAILABLE,  # careers page blocked
            ),
        ]
        assert compute_verdict(evidence) == Verdict.UNVERIFIED


# ---------------------------------------------------------------------------
# UNVERIFIED: the safe default
# ---------------------------------------------------------------------------

class TestUnverified:
    """Unverified is the default — any ambiguity lands here."""

    def test_empty_evidence_list(self):
        assert compute_verdict([]) == Verdict.UNVERIFIED

    def test_all_unavailable(self):
        """Every source failed → unverified, never accuse."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="fee_policy",
                outcome=EvidenceOutcome.UNAVAILABLE,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="domain_age",
                outcome=EvidenceOutcome.UNAVAILABLE,
            ),
        ]
        assert compute_verdict(evidence) == Verdict.UNVERIFIED

    def test_mixed_confirmed_and_unresolved(self):
        """Some checks pass, some unknown → unverified."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="domain_match",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
            EvidenceRecord(
                tier=EvidenceTier.T2_TECHNICAL,
                check="mail_posture",
                outcome=EvidenceOutcome.UNRESOLVED,
            ),
        ]
        assert compute_verdict(evidence) == Verdict.UNVERIFIED


# ---------------------------------------------------------------------------
# Edge cases from the brief's "three distinctions we refuse to blur"
# ---------------------------------------------------------------------------

class TestDistinctionsWeRefuseToBlur:
    """Charging money is not fraud. A real vacancy doesn't authenticate a sender."""

    def test_payment_demand_alone_is_not_high_risk(self):
        """A payment demand with no conflicting evidence → unverified, not high risk.
        Paid training is legal. The conflict is between what they promise and
        what they can evidence."""
        evidence = [
            EvidenceRecord(
                check="payment_demand",
                outcome=EvidenceOutcome.CONFIRMED,
                details={"amount": "15000", "description": "training fee"},
            ),
        ]
        assert compute_verdict(evidence) == Verdict.UNVERIFIED

    def test_real_vacancy_alone_does_not_clear(self):
        """Finding a real vacancy is not enough for 'no conflict found'.
        Copying a genuine job post is the most common scam move."""
        evidence = [
            EvidenceRecord(
                tier=EvidenceTier.T1_AUTHORITATIVE,
                check="vacancy_match",
                outcome=EvidenceOutcome.CONFIRMED,
            ),
        ]
        # Without employer domain confirmation, this is unverified
        assert compute_verdict(evidence) == Verdict.UNVERIFIED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
