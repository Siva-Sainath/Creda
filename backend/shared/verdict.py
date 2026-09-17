"""
Creda — verdict computation.

The model never decides the verdict. This pure function does.
It takes evidence records and returns the real verdict.

Rules (from the build brief):
  HIGH_RISK:          ≥1 T1 conflict, OR 2+ independent T2 signals + payment/identity demand
  UNVERIFIED:         default — any missing, blocked, stale, or ambiguous check
  NO_CONFLICT_FOUND:  employer domain confirmed AND matching vacancy on their own board
                      AND zero conflicts. Never awarded on absence of evidence.

Unit-test this with a fabricated "high risk" model output and zero evidence records
— it must return UNVERIFIED. That test is worth showing a judge.
"""

from __future__ import annotations

from shared.models import (
    EvidenceOutcome,
    EvidenceRecord,
    EvidenceTier,
    Verdict,
)


def compute_verdict(
    evidence: list[EvidenceRecord],
    model_verdict_candidate: str | None = None,
) -> Verdict:
    """
    Compute the real verdict from evidence records.

    ``model_verdict_candidate`` is whatever the LLM suggested — it is
    informational only and **never** overrides the evidence-based rules.

    The function is pure: same evidence in → same verdict out.
    """
    if not evidence:
        # No evidence at all — we know nothing.  Never accuse.
        return Verdict.UNVERIFIED

    # ---- collect signals ----
    t1_conflicts: list[EvidenceRecord] = []
    t2_conflicts: list[EvidenceRecord] = []
    t1_confirmed: list[EvidenceRecord] = []
    all_outcomes: list[EvidenceOutcome] = []

    has_payment_demand = False
    has_identity_demand = False
    has_employer_confirmed = False
    has_vacancy_confirmed = False

    for ev in evidence:
        all_outcomes.append(ev.outcome)

        # Track conflicts by tier
        if ev.outcome == EvidenceOutcome.CONFLICT:
            if ev.tier == EvidenceTier.T1_AUTHORITATIVE:
                t1_conflicts.append(ev)
            elif ev.tier == EvidenceTier.T2_TECHNICAL:
                t2_conflicts.append(ev)
            # T3 conflicts are NEVER allowed to move the verdict

        # Track confirmations
        if ev.outcome == EvidenceOutcome.CONFIRMED:
            if ev.tier == EvidenceTier.T1_AUTHORITATIVE:
                t1_confirmed.append(ev)

        # Track specific check outcomes
        if ev.check == "payment_demand" and ev.outcome == EvidenceOutcome.CONFIRMED:
            has_payment_demand = True
        if ev.check == "identity_demand" and ev.outcome == EvidenceOutcome.CONFIRMED:
            has_identity_demand = True

        # Check for payment demand in details
        if ev.check == "payment_demand" and ev.outcome != EvidenceOutcome.UNAVAILABLE:
            if ev.details.get("amount") or ev.details.get("upi_id") or ev.details.get("bank_account"):
                has_payment_demand = True

        if ev.check == "employer_resolved" and ev.outcome == EvidenceOutcome.CONFIRMED:
            has_employer_confirmed = True
        if ev.check == "domain_match" and ev.outcome == EvidenceOutcome.CONFIRMED:
            has_employer_confirmed = True

        if ev.check == "vacancy_match" and ev.outcome == EvidenceOutcome.CONFIRMED:
            has_vacancy_confirmed = True

    # ---- Rule 1: HIGH RISK ----
    # At least one T1 conflict
    if t1_conflicts:
        return Verdict.HIGH_RISK

    # Two independent T2 signals plus a payment or identity demand
    unique_t2_checks = {ev.check for ev in t2_conflicts}
    if len(unique_t2_checks) >= 2 and (has_payment_demand or has_identity_demand):
        return Verdict.HIGH_RISK

    # ---- Rule 3: NO CONFLICT FOUND ----
    # Employer domain confirmed AND matching vacancy AND zero conflicts across all tiers
    any_conflict = any(o == EvidenceOutcome.CONFLICT for o in all_outcomes)
    any_unavailable = any(o == EvidenceOutcome.UNAVAILABLE for o in all_outcomes)
    any_unresolved = any(o == EvidenceOutcome.UNRESOLVED for o in all_outcomes)

    if (
        has_employer_confirmed
        and has_vacancy_confirmed
        and not any_conflict
        and not any_unavailable
        and not any_unresolved
    ):
        return Verdict.NO_CONFLICT_FOUND

    # ---- Rule 2: UNVERIFIED (default) ----
    return Verdict.UNVERIFIED
