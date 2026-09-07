"""Tests for deterministic verification (verification.py)."""

from __future__ import annotations

import datetime as _dt
import unittest
from dataclasses import replace
from decimal import Decimal

from personal_finance_agent.analytics import (
    category_analysis,
    largest_expenses,
    merchant_analysis,
    period_comparison,
    spending_summary,
)
from personal_finance_agent.models import Period, ResultStatus, SpendingSummary
from personal_finance_agent.verification import (
    VerificationResult,
    verify_category_analysis,
    verify_largest_expenses,
    verify_merchant_analysis,
    verify_period_comparison,
    verify_spending_total,
)
from tests.support import AUGUST, SEPTEMBER, standard_transactions


def failed_message(result: VerificationResult) -> str:
    return "; ".join(check.message for check in result.checks if not check.passed)


class VerifySpendingTotalTests(unittest.TestCase):
    def test_valid_summary_passes(self):
        result = verify_spending_total(
            spending_summary(standard_transactions(), AUGUST), standard_transactions()
        )
        self.assertTrue(result.passed, failed_message(result))

    def test_tampered_total_fails(self):
        summary = spending_summary(standard_transactions(), AUGUST)
        result = verify_spending_total(
            replace(summary, total=Decimal("999.00")), standard_transactions()
        )
        self.assertTrue(result.failed)

    def test_tampered_evidence_fails(self):
        summary = spending_summary(standard_transactions(), AUGUST)
        result = verify_spending_total(
            replace(summary, included_transaction_ids=("t2",)), standard_transactions()
        )
        self.assertTrue(result.failed)

    def test_wrong_count_fails(self):
        summary = spending_summary(standard_transactions(), AUGUST)
        result = verify_spending_total(
            replace(summary, transaction_count=99), standard_transactions()
        )
        self.assertTrue(result.failed)

    def test_unreferenced_transaction_id_fails(self):
        summary = spending_summary(standard_transactions(), AUGUST)
        result = verify_spending_total(
            replace(summary, included_transaction_ids=("ghost",)), standard_transactions()
        )
        self.assertTrue(result.failed)

    def test_error_status_is_inconclusive(self):
        summary = SpendingSummary(
            period=AUGUST,
            currency="",
            total=Decimal("0"),
            transaction_count=0,
            included_transaction_ids=(),
            directions=(),
            status=ResultStatus.ERROR,
            warnings=("period spans multiple currencies; spending cannot be aggregated",),
        )
        result = verify_spending_total(summary, standard_transactions())
        self.assertTrue(result.inconclusive)


class VerifyCategoryAnalysisTests(unittest.TestCase):
    def test_valid_category_analysis_passes(self):
        result = verify_category_analysis(
            category_analysis(standard_transactions(), AUGUST), standard_transactions()
        )
        self.assertTrue(result.passed, failed_message(result))

    def test_tampered_category_total_fails(self):
        analysis = category_analysis(standard_transactions(), AUGUST)
        entries = list(analysis.category_totals)
        bad = replace(entries[0], total=Decimal("999.00"))
        tampered = replace(analysis, category_totals=tuple([bad, *entries[1:]]))
        result = verify_category_analysis(tampered, standard_transactions())
        self.assertTrue(result.failed)

    def test_reconciliation_failure_detected(self):
        analysis = category_analysis(standard_transactions(), AUGUST)
        tampered = replace(analysis, uncovered_amount=Decimal("5.00"))
        result = verify_category_analysis(tampered, standard_transactions())
        self.assertTrue(result.failed)
        self.assertIn("reconcile", failed_message(result))

    def test_wrong_ordering_fails(self):
        analysis = category_analysis(standard_transactions(), AUGUST)
        entries = [entry for entry in analysis.category_totals]
        tampered = replace(analysis, category_totals=tuple(reversed(entries)))
        result = verify_category_analysis(tampered, standard_transactions())
        self.assertTrue(result.failed)


class VerifyMerchantAnalysisTests(unittest.TestCase):
    def test_valid_merchant_analysis_passes(self):
        result = verify_merchant_analysis(
            merchant_analysis(standard_transactions(), AUGUST), standard_transactions()
        )
        self.assertTrue(result.passed, failed_message(result))

    def test_tampered_merchant_total_fails(self):
        analysis = merchant_analysis(standard_transactions(), AUGUST)
        entries = list(analysis.merchants)
        bad = replace(entries[0], total=Decimal("1.00"))
        tampered = replace(analysis, merchants=tuple([bad, *entries[1:]]))
        result = verify_merchant_analysis(tampered, standard_transactions())
        self.assertTrue(result.failed)


class VerifyPeriodComparisonTests(unittest.TestCase):
    def test_valid_comparison_passes(self):
        result = verify_period_comparison(
            period_comparison(standard_transactions(), AUGUST, SEPTEMBER),
            standard_transactions(),
        )
        self.assertTrue(result.passed, failed_message(result))

    def test_tampered_difference_fails(self):
        comparison = period_comparison(standard_transactions(), AUGUST, SEPTEMBER)
        tampered = replace(comparison, absolute_difference=Decimal("1.00"))
        result = verify_period_comparison(tampered, standard_transactions())
        self.assertTrue(result.failed)

    def test_tampered_percentage_fails(self):
        comparison = period_comparison(standard_transactions(), AUGUST, SEPTEMBER)
        tampered = replace(comparison, percentage_difference=Decimal("10.00"))
        result = verify_period_comparison(tampered, standard_transactions())
        self.assertTrue(result.failed)

    def test_tampered_total_fails(self):
        comparison = period_comparison(standard_transactions(), AUGUST, SEPTEMBER)
        tampered = replace(comparison, total_b=Decimal("0"))
        result = verify_period_comparison(tampered, standard_transactions())
        self.assertTrue(result.failed)


class VerifyLargestExpensesTests(unittest.TestCase):
    def test_valid_largest_expenses_passes(self):
        result = verify_largest_expenses(
            largest_expenses(standard_transactions(), AUGUST, limit=2),
            standard_transactions(),
        )
        self.assertTrue(result.passed, failed_message(result))

    def test_tampered_amount_fails(self):
        analysis = largest_expenses(standard_transactions(), AUGUST, limit=2)
        entries = list(analysis.largest)
        bad = replace(entries[0], amount=Decimal("1.00"))
        tampered = replace(analysis, largest=tuple([bad, *entries[1:]]))
        result = verify_largest_expenses(tampered, standard_transactions())
        self.assertTrue(result.failed)

    def test_tampered_order_fails(self):
        analysis = largest_expenses(standard_transactions(), AUGUST, limit=3)
        tampered = replace(analysis, largest=tuple(reversed(analysis.largest)))
        result = verify_largest_expenses(tampered, standard_transactions())
        self.assertTrue(result.failed)

    def test_empty_result_verifies(self):
        empty_period = Period(_dt.date(2025, 8, 20), _dt.date(2025, 8, 21))
        analysis = largest_expenses(standard_transactions(), empty_period)
        result = verify_largest_expenses(analysis, standard_transactions())
        self.assertTrue(result.passed, failed_message(result))


if __name__ == "__main__":
    unittest.main()