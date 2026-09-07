"""Field-level validation of source records.

This module validates the raw text fields loaded by :mod:`data`. Records that
pass structural and semantic validation become typed :class:`ParsedRecord`
objects; records with any problem are returned in :class:`RejectedRecord` with
per-field, human-readable reasons. Invalid records are never silently discarded.

Validation covers (docs/05_data_design.md sections 9.1-9.2):

- required fields are present and non-empty: ``transaction_id``, ``date``,
  ``description``, ``amount``, ``direction``, ``currency``;
- ``date`` is a valid ISO-8601 calendar date (``YYYY-MM-DD``);
- ``amount`` is a positive, finite decimal magnitude (direction is separate,
  so negative, zero, and non-numeric amounts are rejected with explanation);
- ``direction`` maps to a known :class:`Direction` value (case-insensitive);
- ``currency`` is a 3-letter code (case-insensitive, normalized to upper);
- optional fields (``merchant``, ``category``) may be blank and become ``None``.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from .data import RawRecord
from .models import Direction

__all__ = [
    "ParsedRecord",
    "RejectedRecord",
    "ValidationIssue",
    "ValidationOutcome",
    "duplicate_transaction_ids",
    "validate_record",
    "validate_records",
]

_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_CURRENCY_RE = re.compile(r"[A-Za-z]{3}")
_AMOUNT_RE = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation problem for a single field of a source record."""

    field: str
    message: str


@dataclass(frozen=True, slots=True)
class ParsedRecord:
    """A validated source record with typed values, ready for normalization."""

    transaction_id: str
    date: _dt.date
    amount: Decimal
    direction: Direction
    currency: str
    description: str
    merchant: str | None
    category: str | None
    source_reference: str
    row_number: int


@dataclass(frozen=True, slots=True)
class RejectedRecord:
    """A source record that failed validation, with its reasons."""

    source_reference: str
    row_number: int
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    """Result of validating a batch of raw records."""

    accepted: tuple[ParsedRecord, ...] = ()
    rejected: tuple[RejectedRecord, ...] = ()

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)


def validate_record(record: RawRecord) -> ParsedRecord | RejectedRecord:
    """Validate a single raw record, returning a parsed or rejected value."""
    issues: list[ValidationIssue] = []
    fields = record.fields

    transaction_id = _required_text(fields.get("transaction_id"), "transaction_id", issues)
    description = _required_text(fields.get("description"), "description", issues)
    raw_date = _required_text(fields.get("date"), "date", issues)
    raw_amount = _required_text(fields.get("amount"), "amount", issues)
    raw_direction = _required_text(fields.get("direction"), "direction", issues)
    raw_currency = _required_text(fields.get("currency"), "currency", issues)

    parsed_date = _parse_date(raw_date, issues)
    parsed_amount = _parse_amount(raw_amount, issues)
    parsed_direction = _parse_direction(raw_direction, issues)
    parsed_currency = _parse_currency(raw_currency, issues)

    merchant = _optional_text(fields.get("merchant"))
    category = _optional_text(fields.get("category"))

    if issues:
        return RejectedRecord(
            source_reference=record.source_reference,
            row_number=record.row_number,
            issues=tuple(issues),
        )

    return ParsedRecord(
        transaction_id=transaction_id,
        date=parsed_date,
        amount=parsed_amount,
        direction=parsed_direction,
        currency=parsed_currency,
        description=description,
        merchant=merchant,
        category=category,
        source_reference=record.source_reference,
        row_number=record.row_number,
    )


def validate_records(records: Sequence[RawRecord]) -> ValidationOutcome:
    """Validate a sequence of raw records into accepted and rejected sets."""
    accepted: list[ParsedRecord] = []
    rejected: list[RejectedRecord] = []
    for record in records:
        result = validate_record(record)
        if isinstance(result, ParsedRecord):
            accepted.append(result)
        else:
            rejected.append(result)
    return ValidationOutcome(tuple(accepted), tuple(rejected))


def duplicate_transaction_ids(records: Iterable[ParsedRecord]) -> tuple[str, ...]:
    """Return transaction ids appearing more than once, in sorted order.

    Duplicate detection is an explicit report; deduplication policy is deferred
    (docs/05_data_design.md section 8, later-defined policy).
    """
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        if record.transaction_id in seen:
            duplicates.add(record.transaction_id)
        seen.add(record.transaction_id)
    return tuple(sorted(duplicates))


def _required_text(value: object, field_name: str, issues: list[ValidationIssue]) -> str:
    if value is None:
        issues.append(ValidationIssue(field_name, f"{field_name} is required but missing"))
        return ""
    text = str(value).strip()
    if not text:
        issues.append(ValidationIssue(field_name, f"{field_name} is required but empty"))
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_date(value: str, issues: list[ValidationIssue]) -> _dt.date | None:
    if not _ISO_DATE_RE.fullmatch(value):
        issues.append(
            ValidationIssue(
                "date",
                f"date is not a valid ISO-8601 calendar date (expected YYYY-MM-DD): {value!r}",
            )
        )
        return None
    try:
        return _dt.date.fromisoformat(value)
    except ValueError:
        issues.append(
            ValidationIssue("date", f"date is not a real calendar day: {value!r}")
        )
        return None


def _parse_amount(value: str, issues: list[ValidationIssue]) -> Decimal | None:
    if not _AMOUNT_RE.fullmatch(value):
        issues.append(
            ValidationIssue(
                "amount",
                "amount must be a plain non-negative decimal like 42.50 "
                f"(no signs, separators, or exponents): {value!r}",
            )
        )
        return None
    try:
        amount = Decimal(value)
    except InvalidOperation:
        issues.append(
            ValidationIssue("amount", f"amount is not a valid decimal number: {value!r}")
        )
        return None
    if not amount.is_finite():
        issues.append(
            ValidationIssue("amount", f"amount must be a finite number: {value!r}")
        )
        return None
    if amount <= 0:
        issues.append(
            ValidationIssue(
                "amount",
                "amount must be a positive magnitude; direction is stored separately "
                f"(got {value!r})",
            )
        )
        return None
    return amount


def _parse_direction(value: str, issues: list[ValidationIssue]) -> Direction | None:
    normalized = value.lower()
    try:
        return Direction(normalized)
    except ValueError:
        allowed = ", ".join(sorted(direction.value for direction in Direction))
        issues.append(
            ValidationIssue(
                "direction",
                f"direction must be one of: {allowed} (got {value!r})",
            )
        )
        return None


def _parse_currency(value: str, issues: list[ValidationIssue]) -> str | None:
    if not _CURRENCY_RE.fullmatch(value):
        issues.append(
            ValidationIssue(
                "currency",
                f"currency must be a 3-letter code (e.g. USD): {value!r}",
            )
        )
        return None
    return value.upper()

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)