"""End-to-end pipeline test: CSV -> validation -> normalization -> analytics -> verification.

This mirrors the documented data flow (docs/06_implementation.md section 11) and
exercises the complete deterministic foundation against the committed synthetic
sample.
"""

from __future__ import annotations

import unittest

from personal_finance_agent.analytics import (
    category_analysis,
    largest_expenses,
    merchant_analysis,
    period_comparison,
    spending_summary,
)
from personal_finance_agent.data import load_csv
from personal_finance_agent.models import Period
from personal_finance_agent.normalization import normalize_records
from personal_finance_agent.synthetic import SYNTHETIC_CSV_PATH
from personal_finance_agent.validation import duplicate_transaction_ids, validate_records
from personal_finance_agent.verification import (
    verify_category_analysis,
    verify_largest_expenses,
    verify_merchant_analysis,
    verify_period_comparison,
    verify_spending_total,
)


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loaded = load_csv(SYNTHETIC_CSV_PATH)
        validated = validate_records(loaded.raw_records)
        cls.transactions = normalize_records(validated.accepted)
        cls.august = Period.for_month(2025, 8)
        cls.september = Period.for_month(2025, 9)

    def test_data_is_canonical(self):
        self.assertGreater(len(self.transactions), 0)
        self.assertEqual(
            duplicate_transaction_ids(validate_records(load_csv(SYNTHETIC_CSV_PATH).raw_records).accepted),
            (),
        )

    def test_spending_summary_verified(self):
        summary = spending_summary(self.transactions, self.august)
        self.assertEqual(summary.status.value, "success")
        verification = verify_spending_total(summary, self.transactions)
        self.assertTrue(verification.passed, [c.message for c in verification.checks if not c.passed])

    def test_category_analysis_verified(self):
        analysis = category_analysis(self.transactions, self.september)
        verification = verify_category_analysis(analysis, self.transactions)
        self.assertTrue(verification.passed, [c.message for c in verification.checks if not c.passed])

    def test_period_comparison_verified_and_interesting(self):
        comparison = period_comparison(self.transactions, self.august, self.september)
        verification = verify_period_comparison(comparison, self.transactions)
        self.assertTrue(verification.passed, [c.message for c in verification.checks if not c.passed])
        self.assertNotEqual(comparison.total_a, comparison.total_b)

    def test_merchant_analysis_verified(self):
        analysis = merchant_analysis(self.transactions, self.august)
        verification = verify_merchant_analysis(analysis, self.transactions)
        self.assertTrue(verification.passed, [c.message for c in verification.checks if not c.passed])

    def test_largest_expenses_verified(self):
        analysis = largest_expenses(self.transactions, self.august, limit=3)
        verification = verify_largest_expenses(analysis, self.transactions)
        self.assertTrue(verification.passed, [c.message for c in verification.checks if not c.passed])
        self.assertEqual(analysis.largest[0].rank, 1)


if __name__ == "__main__":
    unittest.main()