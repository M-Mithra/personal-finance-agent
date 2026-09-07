"""Tests for field-level validation (validation.py)."""

from __future__ import annotations

import datetime as _dt
import unittest
from decimal import Decimal

from personal_finance_agent.data import RawRecord
from personal_finance_agent.models import Direction
from personal_finance_agent.validation import (
    ParsedRecord,
    RejectedRecord,
    duplicate_transaction_ids,
    validate_record,
    validate_records,
)

VALID = {
    "transaction_id": "tx1",
    "date": "2025-08-01",
    "description": "Groceries",
    "merchant": "FreshMart",
    "amount": "42.50",
    "direction": "expense",
    "category": "Groceries",
    "currency": "USD",
}


def record(fields: dict | None = None, row_number: int = 2) -> RawRecord:
    data = dict(VALID)
    if fields:
        data.update(fields)
    return RawRecord(row_number=row_number, fields=data, source_reference=f"t.csv:{row_number}")


class ValidateRecordTests(unittest.TestCase):
    def test_valid_record_parsed_with_typed_fields(self):
        result = validate_record(record())
        self.assertIsInstance(result, ParsedRecord)
        assert isinstance(result, ParsedRecord)
        self.assertEqual(result.transaction_id, "tx1")
        self.assertEqual(result.date, _dt.date(2025, 8, 1))
        self.assertEqual(result.amount, Decimal("42.50"))
        self.assertIs(result.direction, Direction.EXPENSE)
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.merchant, "FreshMart")
        self.assertEqual(result.category, "Groceries")

    def test_case_insensitive_direction_and_currency(self):
        result = validate_record(record({"direction": "EXPENSE", "currency": "usd"}))
        self.assertIsInstance(result, ParsedRecord)
        assert isinstance(result, ParsedRecord)
        self.assertIs(result.direction, Direction.EXPENSE)
        self.assertEqual(result.currency, "USD")

    def test_optional_fields_may_be_blank(self):
        result = validate_record(record({"merchant": " ", "category": ""}))
        self.assertIsInstance(result, ParsedRecord)
        assert isinstance(result, ParsedRecord)
        self.assertIsNone(result.merchant)
        self.assertIsNone(result.category)

    def test_missing_required_fields_are_rejected_with_reasons(self):
        result = validate_record(record({"transaction_id": "", "date": ""}))
        self.assertIsInstance(result, RejectedRecord)
        assert isinstance(result, RejectedRecord)
        self.assertTrue(any(issue.field == "transaction_id" for issue in result.issues))
        self.assertTrue(any(issue.field == "date" for issue in result.issues))

    def test_invalid_date_rejected(self):
        for bad in ("2025-8-1", "2025/08/01", "2025-13-01", "2025-02-30", "not-a-date"):
            result = validate_record(record({"date": bad}))
            self.assertIsInstance(result, RejectedRecord, msg=f"date={bad!r}")
            assert isinstance(result, RejectedRecord)
            self.assertTrue(any(issue.field == "date" for issue in result.issues))

    def test_invalid_amount_rejected(self):
        for bad in ("-42.50", "0", "abc", "NaN", "Infinity", "1_000"):
            result = validate_record(record({"amount": bad}))
            self.assertIsInstance(result, RejectedRecord, msg=f"amount={bad!r}")
            assert isinstance(result, RejectedRecord)
            self.assertTrue(any(issue.field == "amount" for issue in result.issues))

    def test_invalid_direction_rejected(self):
        result = validate_record(record({"direction": "withdrawal"}))
        self.assertIsInstance(result, RejectedRecord)
        assert isinstance(result, RejectedRecord)
        self.assertTrue(any(issue.field == "direction" for issue in result.issues))

    def test_invalid_currency_rejected(self):
        for bad in ("US", "USDD", "USD1"):
            result = validate_record(record({"currency": bad}))
            self.assertIsInstance(result, RejectedRecord, msg=f"currency={bad!r}")

    def test_shared_validation_accepts_all_valid_directions(self):
        for direction in ("expense", "income", "transfer", "refund", "unresolved"):
            result = validate_record(record({"direction": direction}))
            self.assertIsInstance(result, ParsedRecord, msg=direction)


class ValidateRecordsTests(unittest.TestCase):
    def test_batch_splits_accepted_and_rejected(self):
        outcome = validate_records([record(), record({"amount": "nope"}), record({"date": "x"})])
        self.assertEqual(outcome.accepted_count, 1)
        self.assertEqual(outcome.rejected_count, 2)

    def test_duplicate_detection(self):
        outcome = validate_records([record({"transaction_id": "dup"}), record({"transaction_id": "dup"}), record({"transaction_id": "other"})])
        self.assertEqual(duplicate_transaction_ids(outcome.accepted), ("dup",))


if __name__ == "__main__":
    unittest.main()