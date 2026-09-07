"""Tests for normalization (normalization.py)."""

from __future__ import annotations

import unittest
from decimal import Decimal

from personal_finance_agent.models import CategoryOrigin, Direction, NormalizationStatus
from personal_finance_agent.normalization import normalize_record
from personal_finance_agent.validation import ParsedRecord


def parsed(
    description: str = "  Groceries   &  Basics  ",
    merchant: str | None = "  FreshMart  ",
    category: str | None = " Groceries ",
) -> ParsedRecord:
    return ParsedRecord(
        transaction_id="tx1",
        date=__import__("datetime").date(2025, 8, 1),
        amount=Decimal("42.50"),
        direction=Direction.EXPENSE,
        currency="USD",
        description=description,
        merchant=merchant,
        category=category,
        source_reference="t.csv:2",
        row_number=2,
    )


class NormalizeRecordTests(unittest.TestCase):
    def test_whitespace_is_collapsed_in_canonical_text(self):
        transaction = normalize_record(parsed())
        self.assertEqual(transaction.description, "Groceries & Basics")
        self.assertEqual(transaction.merchant, "FreshMart")
        self.assertEqual(transaction.category, "Groceries")

    def test_original_description_preserved_exactly(self):
        transaction = normalize_record(parsed())
        self.assertEqual(transaction.original_description, "  Groceries   &  Basics  ")
        self.assertNotEqual(transaction.description, transaction.original_description)

    def test_normalized_description_is_lowercase_comparison_aid(self):
        transaction = normalize_record(parsed(description="Groceries & Basics"))
        self.assertEqual(transaction.normalized_description, "groceries & basics")

    def test_source_category_preserved_with_source_origin(self):
        transaction = normalize_record(parsed())
        self.assertEqual(transaction.category, "Groceries")
        self.assertIs(transaction.category_origin, CategoryOrigin.SOURCE)

    def test_missing_category_becomes_none_with_unresolved_origin(self):
        transaction = normalize_record(parsed(category=None))
        self.assertIsNone(transaction.category)
        self.assertIs(transaction.category_origin, CategoryOrigin.UNRESOLVED)

    def test_missing_merchant_becomes_none(self):
        transaction = normalize_record(parsed(merchant=None))
        self.assertIsNone(transaction.merchant)

    def test_normalization_status(self):
        changed = normalize_record(parsed(description="  Prefix Appended  "))
        self.assertIs(changed.normalization_status, NormalizationStatus.NORMALIZED)
        untouched = normalize_record(parsed(description="Plain", merchant="Clean", category="Neat"))
        self.assertIs(untouched.normalization_status, NormalizationStatus.AS_SUPPLIED)

    def test_source_reference_and_amount_carried_through(self):
        transaction = normalize_record(parsed())
        self.assertEqual(transaction.source_reference, "t.csv:2")
        self.assertEqual(transaction.amount, Decimal("42.50"))
        self.assertEqual(transaction.currency, "USD")


if __name__ == "__main__":
    unittest.main()