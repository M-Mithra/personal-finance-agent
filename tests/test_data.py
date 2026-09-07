"""Tests for CSV loading (data.py)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from personal_finance_agent.data import REQUIRED_COLUMNS, load_csv

HEADER = "transaction_id,date,description,merchant,amount,direction,category,currency"
VALID_ROW = "tx1,2025-08-01,Groceries,FreshMart,42.50,expense,Groceries,USD"


def write_csv(lines: list[str]) -> Path:
    temp_dir = tempfile.mkdtemp()
    path = Path(temp_dir) / "transactions.csv"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


class LoadCsvTests(unittest.TestCase):
    def test_loads_valid_csv_into_raw_records(self):
        path = write_csv([HEADER, VALID_ROW, "tx2,2025-09-05,Dinner,Sushi House,55.00,expense,Dining,USD"])
        outcome = load_csv(path)
        self.assertTrue(outcome.loaded_cleanly)
        self.assertEqual(outcome.record_count, 2)
        self.assertEqual(outcome.raw_records[0].fields["transaction_id"], "tx1")
        self.assertEqual(outcome.raw_records[0].row_number, 2)
        self.assertEqual(outcome.raw_records[0].source_reference, "transactions.csv:2")

    def test_blank_lines_are_skipped_without_error(self):
        path = write_csv([HEADER, "", VALID_ROW, "   ", ""])
        outcome = load_csv(path)
        self.assertTrue(outcome.loaded_cleanly)
        self.assertEqual(outcome.record_count, 1)

    def test_empty_file_reports_structural_issue(self):
        path = write_csv([])
        outcome = load_csv(path)
        self.assertEqual(outcome.record_count, 0)
        self.assertFalse(outcome.loaded_cleanly)
        self.assertIn("empty", outcome.issues[0].message)

    def test_file_without_useful_header_is_rejected(self):
        # The first non-blank row is treated as the header; a data-only file is
        # reported as missing the required columns rather than parsed silently.
        path = write_csv(["tx1,2025-08-01,42.50"])
        outcome = load_csv(path)
        self.assertEqual(outcome.record_count, 0)
        self.assertFalse(outcome.loaded_cleanly)
        self.assertTrue(any("missing required column" in issue.message for issue in outcome.issues))

    def test_missing_required_column_reports_all_missing(self):
        path = write_csv(["date,amount", "2025-08-01,42.50"])
        outcome = load_csv(path)
        self.assertEqual(outcome.record_count, 0)
        messages = " ".join(issue.message for issue in outcome.issues)
        for column in REQUIRED_COLUMNS:
            if column in ("date", "amount"):
                continue
            self.assertIn(column, messages)

    def test_duplicate_columns_are_rejected(self):
        path = write_csv(["transaction_id,date,amount,amount,direction", "tx1,2025-08-01,10,10,expense"])
        outcome = load_csv(path)
        self.assertEqual(outcome.record_count, 0)
        self.assertIn("duplicate", " ".join(issue.message for issue in outcome.issues))

    def test_row_with_extra_cells_is_excluded_with_issue(self):
        path = write_csv([HEADER, VALID_ROW, VALID_ROW + ",EXTRA"])
        outcome = load_csv(path)
        self.assertEqual(outcome.record_count, 1)
        self.assertFalse(outcome.loaded_cleanly)
        self.assertIn("extra", outcome.issues[0].message)
        self.assertEqual(outcome.raw_records[0].fields["transaction_id"], "tx1")

    def test_row_shorter_than_header_is_padded_and_loaded(self):
        path = write_csv([HEADER, "tx1,2025-08-01,Groceries"])
        outcome = load_csv(path)
        self.assertEqual(outcome.record_count, 1)
        self.assertEqual(outcome.raw_records[0].fields["amount"], "")

    def test_missing_file_raises_filenotfound(self):
        with self.assertRaises(FileNotFoundError):
            load_csv(Path("/nonexistent/path/transactions.csv"))


if __name__ == "__main__":
    unittest.main()