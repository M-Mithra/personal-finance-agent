"""CSV source loading for the deterministic foundation.

Loading is deliberately separated from validation: this module only reads a CSV
file into raw text records and reports structural (file-level / row-shape)
problems as ``LoadIssue`` objects. Field-level validation of the raw values
lives in :mod:`personal_finance_agent.validation`.

Source format for the first vertical slice (measured against
``docs/06_implementation.md`` section 10.1):

    transaction_id,date,description,merchant,amount,direction,category,currency

- ``date``:  ISO 8601 calendar date (YYYY-MM-DD).
- ``amount``: positive decimal magnitude; direction is a separate column.
- ``direction``: one of ``expense``, ``income``, ``transfer``, ``refund``,
  ``unresolved`` (case-insensitive).
- ``merchant``/``category``: optional, may be blank.
- ``currency``: 3-letter currency code (case-insensitive).

Structural problems handled here: empty file, missing/duplicate header columns,
rows with extra values beyond the header, and blank lines (a blank line contains
no record and is skipped). Missing field *values* and semantic problems are left
to validation so that the loader stays format-focused.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

__all__ = [
    "DataError",
    "LoadIssue",
    "LoadOutcome",
    "RawRecord",
    "REQUIRED_COLUMNS",
    "load_csv",
]

REQUIRED_COLUMNS: tuple[str, ...] = (
    "transaction_id",
    "date",
    "description",
    "merchant",
    "amount",
    "direction",
    "category",
    "currency",
)


class DataError(Exception):
    """Raised when a source file cannot be read at all (e.g. decode failure)."""


@dataclass(frozen=True, slots=True)
class LoadIssue:
    """A structural problem found while loading a CSV file.

    ``row_number`` is ``None`` for file-level issues (e.g. header problems).
    """

    row_number: int | None
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class RawRecord:
    """One source row preserved as raw text, before any field validation."""

    row_number: int
    fields: Mapping[str, str]
    source_reference: str


@dataclass(frozen=True, slots=True)
class LoadOutcome:
    """Result of loading a CSV file: raw records plus structural issues."""

    path: Path
    raw_records: tuple[RawRecord, ...] = ()
    issues: tuple[LoadIssue, ...] = ()

    @property
    def record_count(self) -> int:
        return len(self.raw_records)

    @property
    def loaded_cleanly(self) -> bool:
        return not self.issues


def load_csv(path: str | Path) -> LoadOutcome:
    """Read ``path`` into raw records, reporting structural issues explicitly.

    Raises :class:`DataError` when the file exists but cannot be decoded, and
    lets :class:`FileNotFoundError` propagate when the path does not exist.
    """
    csv_path = Path(path)
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    except UnicodeDecodeError as exc:  # pragma: no cover - platform-specific
        raise DataError(f"cannot decode {csv_path} as UTF-8 text: {exc}") from exc

    issues: list[LoadIssue] = []
    records: list[RawRecord] = []

    if not rows:
        return LoadOutcome(csv_path, (), (LoadIssue(None, "file", "file is empty"),))

    header_index = 0
    while header_index < len(rows) and _is_blank_row(rows[header_index]):
        header_index += 1
    if header_index >= len(rows):
        return LoadOutcome(
            csv_path, (), (LoadIssue(None, "file", "file contains no header row"),)
        )

    header = [cell.strip() for cell in rows[header_index]]
    duplicated = sorted({name for name in header if header.count(name) > 1})
    if duplicated:
        issues.append(
            LoadIssue(header_index + 1, "header", f"duplicate column(s): {duplicated}")
        )
    missing = [name for name in REQUIRED_COLUMNS if name not in header]
    if missing:
        issues.append(
            LoadIssue(
                header_index + 1,
                "header",
                f"missing required column(s): {missing}",
            )
        )
    if duplicated or missing:
        return LoadOutcome(csv_path, (), tuple(issues))

    for relative_index, row in enumerate(rows[header_index + 1 :], start=1):
        row_number = header_index + 1 + relative_index
        if _is_blank_row(row):
            # A blank line carries no record; it is not a rejection.
            continue
        if len(row) > len(header):
            issues.append(
                LoadIssue(
                    row_number,
                    "row",
                    f"row has {len(row) - len(header)} extra value(s) beyond the "
                    f"header columns; record excluded",
                )
            )
            continue
        padded = list(row) + [""] * (len(header) - len(row))
        fields = {column: cell for column, cell in zip(header, padded)}
        records.append(
            RawRecord(
                row_number=row_number,
                fields=fields,
                source_reference=f"{csv_path.name}:{row_number}",
            )
        )

    return LoadOutcome(csv_path, tuple(records), tuple(issues))


def _is_blank_row(row: list[str]) -> bool:
    return not any((cell or "").strip() for cell in row)