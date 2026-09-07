"""Wiring between tool results and the deterministic verification layer.

After a tool produces a result, the runtime passes it here to be independently
checked against the canonical transactions. This module maps each tool name to
the corresponding ``verify_*`` function in
:mod:`personal_finance_agent.verification` and classifies the outcome into a
trust level the runtime can act on:

* ``verified`` — all verification checks passed;
* ``failed`` — at least one check disagreed (result must not be trusted);
* ``inconclusive`` — the result could not be verified (typically an error
  result with no numeric content);
* ``unverified`` — verification was not performed (e.g. no matching verifier).
"""

from __future__ import annotations

from collections.abc import Sequence

from ..models import (
    CategoryAnalysis,
    MerchantAnalysis,
    NoteworthyAnalysis,
    PeriodComparison,
    SpendingSummary,
    Transaction,
)
from ..verification import (
    VerificationResult,
    verify_category_analysis,
    verify_largest_expenses,
    verify_merchant_analysis,
    verify_period_comparison,
    verify_spending_total,
)

__all__ = [
    "TRUST_VERIFIED",
    "TRUST_FAILED",
    "TRUST_INCONCLUSIVE",
    "TRUST_UNVERIFIED",
    "classify_trust",
    "verify_for",
]

TRUST_VERIFIED = "verified"
TRUST_FAILED = "failed"
TRUST_INCONCLUSIVE = "inconclusive"
TRUST_UNVERIFIED = "unverified"

_VERIFIERS = {
    "spending_summary": (verify_spending_total, SpendingSummary),
    "category_analysis": (verify_category_analysis, CategoryAnalysis),
    "period_comparison": (verify_period_comparison, PeriodComparison),
    "merchant_analysis": (verify_merchant_analysis, MerchantAnalysis),
    "noteworthy_transactions": (verify_largest_expenses, NoteworthyAnalysis),
}


def _classify(result: VerificationResult) -> str:
    """Map a VerificationResult status to a trust level."""
    if result.status == "passed":
        return TRUST_VERIFIED
    if result.status == "failed":
        return TRUST_FAILED
    return TRUST_INCONCLUSIVE


def classify_trust(result: VerificationResult) -> str:
    """Public trust classifier (see module docstring)."""
    return _classify(result)


def verify_for(
    tool_name: str,
    result: object,
    transactions: Sequence[Transaction],
) -> tuple[str, VerificationResult | None]:
    """Verify a tool result and return ``(trust, verification_result)``.

    Returns ``(TRUST_UNVERIFIED, None)`` when no verifier is registered for the
    tool. Never trusts a result on its own: the returned verification detail
    always comes from an independent recomputation.
    """
    entry = _VERIFIERS.get(tool_name)
    if entry is None:
        return TRUST_UNVERIFIED, None

    verifier, expected_type = entry
    if not isinstance(result, expected_type):
        return TRUST_UNVERIFIED, None

    verification = verifier(result, transactions)
    return _classify(verification), verification
