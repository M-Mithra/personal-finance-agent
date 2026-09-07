"""Tests for deterministic analytical capabilities (analytics.py)."""

from __future__ import annotations

import datetime as _dt
import unittest
from decimal import Decimal

from personal_finance_agent.analytics import (
    category_analysis,
    largest_expenses,
    merchant_analysis,
    percentage_change,
    period_comparison,
    spending_summary,
    transactions_in_period,
)
from personal_finance_agent.models import Period, ResultStatus
from tests.support import AUGUST, SEPTEMBER, standard_transactions, tx

TOTAL_AUG = Decimal("400.00")
TOTAL_SEP = Decimal("780.00")


class SpendingSummaryTests(unittest.TestCase):
    def test_august_total_includes_only_expenses(self):
        result = spending_summary(standard_transactions(), AUGUST)
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.total, TOTAL_AUG)
        self.assertEqual(result.transaction_count, 3)
        self.assertEqual(result.included_transaction_ids, ("t1", "t2", "t3"))
        self.assertEqual(result.currency, "USD")

    def test_period_boundaries_are_inclusive(self):
        result = spending_summary(standard_transactions(), AUGUST)
        # t1 on Aug 1 and t3 on Aug 31 are included; t8 (Jul 31) and t9 (Sep 30) are not.
        self.assertEqual(result.included_transaction_ids, ("t1", "t2", "t3"))

    def test_income_and_refund_are_never_treated_as_spending(self):
        result = spending_summary(standard_transactions(), AUGUST)
        self.assertNotIn("t4", result.included_transaction_ids)
        self.assertNotIn("t5", result.included_transaction_ids)

    def test_empty_period_returns_empty_status_and_zero(self):
        empty_period = Period(_dt.date(2025, 8, 20), _dt.date(2025, 8, 25))
        result = spending_summary(standard_transactions(), empty_period)
        self.assertEqual(result.status, ResultStatus.EMPTY)
        self.assertEqual(result.total, Decimal("0"))
        self.assertEqual(result.transaction_count, 0)
        self.assertTrue(result.warnings)

    def test_period_with_no_matching_direction_returns_empty(self):
        # No transfer records exist in the fixture, so nothing matches.
        result = spending_summary(standard_transactions(), AUGUST, directions=("transfer",))
        self.assertEqual(result.status, ResultStatus.EMPTY)
        self.assertEqual(result.total, Decimal("0"))

    def test_mixed_currency_scope_returns_error(self):
        transactions = standard_transactions()
        transactions.append(
            tx("t100", 5, "10.00", currency="EUR", merchant=None, category=None)
        )
        result = spending_summary(transactions, AUGUST)
        self.assertEqual(result.status, ResultStatus.ERROR)
        self.assertIn("multiple currencies", result.warnings[0])

    def test_currency_filter_scopes_selection(self):
        transactions = standard_transactions()
        transactions.append(
            tx("t100", 5, "10.00", currency="EUR", merchant=None, category=None)
        )
        result = spending_summary(transactions, AUGUST, currency="USD")
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.total, TOTAL_AUG)

    def test_transactions_in_period_raises_on_mixed_currencies(self):
        transactions = standard_transactions()
        transactions.append(
            tx("t100", 5, "10.00", currency="EUR", merchant=None, category=None)
        )
        with self.assertRaises(ValueError):
            transactions_in_period(transactions, AUGUST)


class CategorySummaryTests(unittest.TestCase):
    def test_category_totals_ordered_and_cover_total(self):
        result = category_analysis(standard_transactions(), AUGUST)
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.total_spending, TOTAL_AUG)
        self.assertEqual(
            [(entry.category, entry.total) for entry in result.category_totals],
            [
                ("Housing", Decimal("250.00")),
                ("Groceries", Decimal("100.00")),
                ("Entertainment", Decimal("50.00")),
            ],
        )
        self.assertEqual(result.uncovered_amount, Decimal("0"))

    def test_uncovered_transactions_visible_and_reconcile(self):
        transactions = standard_transactions()
        transactions.append(
            tx("t11", 8, "33.00", merchant="NoCategory", category=None)
        )
        result = category_analysis(transactions, AUGUST)
        self.assertEqual(result.uncovered_amount, Decimal("33.00"))
        self.assertEqual(result.uncovered_transaction_ids, ("t11",))
        covered = sum((entry.total for entry in result.category_totals), Decimal("0"))
        self.assertEqual(covered + result.uncovered_amount, result.total_spending)


class MerchantAnalysisTests(unittest.TestCase):
    def test_merchant_ranking_by_total_descending(self):
        result = merchant_analysis(standard_transactions(), AUGUST)
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(
            [entry.merchant for entry in result.merchants],
            ["Metro", "FreshMart", "Cinema7"],
        )
        self.assertEqual(result.merchants[0].total, Decimal("250.00"))
        self.assertEqual(result.merchants[0].transaction_ids, ("t2",))

    def test_merchant_totals_reconcile_with_total(self):
        result = merchant_analysis(standard_transactions(), AUGUST)
        attributed = sum((entry.total for entry in result.merchants), Decimal("0"))
        self.assertEqual(attributed + result.unattributed_amount, result.total_spending)


class PeriodComparisonTests(unittest.TestCase):
    def test_comparison_math_and_direction(self):
        result = period_comparison(standard_transactions(), AUGUST, SEPTEMBER)
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.total_a, TOTAL_AUG)
        self.assertEqual(result.total_b, TOTAL_SEP)
        self.assertEqual(result.absolute_difference, TOTAL_SEP - TOTAL_AUG)
        self.assertEqual(result.percentage_difference, Decimal("95.00"))
        self.assertEqual(result.change_direction, "increase")

    def test_zero_baseline_qualifies_percentage(self):
        zero = Period(_dt.date(2025, 8, 20), _dt.date(2025, 8, 21))
        comparison = period_comparison(standard_transactions(), zero, AUGUST)
        self.assertEqual(comparison.total_a, Decimal("0"))
        self.assertIsNone(comparison.percentage_difference)
        self.assertEqual(comparison.change_direction, "increase")
        self.assertTrue(any("percentage" in warning for warning in comparison.warnings))


class LargestExpensesTests(unittest.TestCase):
    def test_top_expenses_ordered(self):
        result = largest_expenses(standard_transactions(), AUGUST, limit=2)
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual([entry.transaction_id for entry in result.largest], ["t2", "t1"])
        self.assertEqual(result.largest[0].rank, 1)
        self.assertEqual(result.largest[0].amount, Decimal("250.00"))

    def test_returns_all_when_fewer_than_limit(self):
        result = largest_expenses(standard_transactions(), AUGUST, limit=10)
        self.assertEqual(len(result.largest), 3)

    def test_ties_broken_by_transaction_id(self):
        transactions = [
            tx("t10", 1, "50.00"),
            tx("t11", 2, "50.00"),
            tx("t12", 3, "50.00"),
        ]
        result = largest_expenses(transactions, AUGUST, limit=3)
        self.assertEqual(
            [entry.transaction_id for entry in result.largest], ["t10", "t11", "t12"]
        )

    def test_invalid_limit_rejected(self):
        with self.assertRaises(ValueError):
            largest_expenses(standard_transactions(), AUGUST, limit=0)

    def test_empty_period(self):
        empty_period = Period(_dt.date(2025, 8, 20), _dt.date(2025, 8, 21))
        result = largest_expenses(standard_transactions(), empty_period)
        self.assertEqual(result.status, ResultStatus.EMPTY)
        self.assertEqual(result.largest, ())


class PercentageChangeTests(unittest.TestCase):
    def test_percentage_change(self):
        self.assertEqual(percentage_change(Decimal("400"), Decimal("780")), Decimal("95.00"))
        self.assertEqual(percentage_change(Decimal("780"), Decimal("400")), Decimal("-48.72"))

    def test_zero_previous_returns_none(self):
        self.assertIsNone(percentage_change(Decimal("0"), Decimal("10")))


if __name__ == "__main__":
    unittest.main()
