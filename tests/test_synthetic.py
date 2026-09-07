"""Tests for the deterministic synthetic dataset (synthetic.py + data/sample)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from personal_finance_agent.data import load_csv
from personal_finance_agent.models import Direction
from personal_finance_agent.synthetic import (
    MONTHS,
    SYNTHETIC_CSV_PATH,
    YEAR,
    build_synthetic_transactions,
    write_synthetic_transactions_csv,
)
from personal_finance_agent.validation import validate_records


class SyntheticGeneratorTests(unittest.TestCase):
    def test_generation_is_deterministic(self):
        self.assertEqual(
            build_synthetic_transactions(), build_synthetic_transactions()
        )

    def test_minimum_size_and_months(self):
        rows = build_synthetic_transactions()
        self.assertGreaterEqual(len(rows), 40)
        months = {row["date"][:7] for row in rows}
        self.assertEqual(months, {f"{YEAR}-{month:02d}" for month in MONTHS})

    def test_directions_covered_and_allowed(self):
        rows = build_synthetic_transactions()
        directions = {row["direction"] for row in rows}
        self.assertLessEqual(directions, set(Direction))
        for expected in ("expense", "income", "refund", "transfer"):
            self.assertIn(expected, directions)

    def test_unique_ids_and_positive_amounts(self):
        rows = build_synthetic_transactions()
        ids = [row["transaction_id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        for row in rows:
            self.assertGreater(float(row["amount"]), 0)

    def test_categories_present(self):
        rows = build_synthetic_transactions()
        categories = {row["category"] for row in rows}
        self.assertIn("Housing", categories)
        self.assertIn("Groceries", categories)
        self.assertIn("Travel", categories)  # August-only variation

    def test_committed_sample_matches_generator(self):
        self.assertTrue(SYNTHETIC_CSV_PATH.exists(), "sample CSV missing")
        with tempfile.TemporaryDirectory() as temp_dir:
            regenerated = write_synthetic_transactions_csv(
                Path(temp_dir) / "transactions.csv"
            )
            self.assertEqual(
                regenerated.read_text(encoding="utf-8"),
                SYNTHETIC_CSV_PATH.read_text(encoding="utf-8"),
                "data/sample/transactions.csv is out of sync with the generator; "
                "regenerate it with write_synthetic_transactions_csv()",
            )


class SyntheticDatasetQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outcome = load_csv(SYNTHETIC_CSV_PATH)
        cls.outcome_validation = validate_records(cls.outcome.raw_records)

    def test_sample_loads_cleanly(self):
        self.assertTrue(self.outcome.loaded_cleanly, self.outcome.issues)

    def test_every_row_is_valid(self):
        self.assertEqual(self.outcome_validation.rejected_count, 0)
        self.assertGreater(self.outcome_validation.accepted_count, 0)

    def test_two_complete_months_present(self):
        months = {record.fields["date"][:7] for record in self.outcome.raw_records}
        self.assertEqual(months, {"2025-08", "2025-09"})


if __name__ == "__main__":
    unittest.main()