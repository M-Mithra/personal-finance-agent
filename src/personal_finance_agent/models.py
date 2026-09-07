"""Canonical domain model for the Personal Finance Agent analytical foundation.

This module defines the canonical transaction representation, the enums that give
transaction fields precise semantics, the temporal ``Period`` type shared by every
analytical capability, and the structured result dataclasses returned by the
analytical functions.

The canonical model follows ``docs/05_data_design.md`` section 6.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

__all__ = [
    "CategoryAnalysis",
    "CategoryOrigin",
    "CategoryTotal",
    "DataQualityStatus",
    "Direction",
    "LargestExpense",
    "MerchantAnalysis",
    "MerchantTotal",
    "NormalizationStatus",
    "NoteworthyAnalysis",
    "Period",
    "PeriodComparison",
    "ResultStatus",
    "SpendingSummary",
    "Transaction",
]


class Direction(StrEnum):
    """Transaction direction semantics.

    ``amount`` is always the absolute magnitude; ``direction`` is stored
    separately (data design section 7.1). Only ``EXPENSE`` counts as spending
    under the default analytical rules.
    """

    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"
    REFUND = "refund"
    UNRESOLVED = "unresolved"


class CategoryOrigin(StrEnum):
    """Where a transaction's category value came from."""

    SOURCE = "source"
    DERIVED = "derived"
    UNRESOLVED = "unresolved"
    NOT_APPLICABLE = "not_applicable"


class DataQualityStatus(StrEnum):
    """Usability summary for a canonical transaction."""

    USABLE = "usable"
    FLAGGED = "flagged"
    INCOMPLETE = "incomplete"


class NormalizationStatus(StrEnum):
    """Whether normalization transformed the record or left it as supplied."""

    NORMALIZED = "normalized"
    AS_SUPPLIED = "as_supplied"
    UNCERTAIN = "uncertain"


class ResultStatus(StrEnum):
    """Outcome of an analytical capability."""

    SUCCESS = "success"
    EMPTY = "empty"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Transaction:
    """Canonical transaction record.

    ``amount`` is the absolute monetary magnitude; ``direction`` is stored
    separately. Arithmetic must never mix currencies: every analytical result
    carries an explicit ``currency``.
    """

    transaction_id: str
    date: _dt.date
    amount: Decimal
    direction: Direction
    currency: str
    description: str
    merchant: str | None = None
    category: str | None = None
    category_origin: CategoryOrigin = CategoryOrigin.UNRESOLVED
    original_description: str = ""
    normalized_description: str = ""
    source_reference: str = ""
    data_quality_status: DataQualityStatus = DataQualityStatus.USABLE
    quality_notes: tuple[str, ...] = ()
    normalization_status: NormalizationStatus = NormalizationStatus.AS_SUPPLIED
@dataclass(frozen=True, slots=True)
class Period:
    """Explicit, inclusive ``[start, end]`` date period.

    Period boundaries follow the data design (section 14): every analytical
    capability makes its boundaries explicit, and a transaction belongs to the
    period when ``start <= date <= end``.
    """

    start: _dt.date
    end: _dt.date
    label: str | None = None

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(
                f"period end {self.end.isoformat()} precedes start {self.start.isoformat()}"
            )
        if self.label is None:
            object.__setattr__(
                self, "label", f"{self.start.isoformat()}..{self.end.isoformat()}"
            )

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, day: _dt.date) -> bool:
        return self.start <= day <= self.end

    @classmethod
    def for_month(cls, year: int, month: int) -> "Period":
        if month == 12:
            end = _dt.date(year + 1, 1, 1) - _dt.timedelta(days=1)
        else:
            end = _dt.date(year, month + 1, 1) - _dt.timedelta(days=1)
        return cls(start=_dt.date(year, month, 1), end=end, label=f"{year:04d}-{month:02d}")


@dataclass(frozen=True, slots=True)
class SpendingSummary:
    """Structured result of the spending-total capability."""

    period: Period
    currency: str
    total: Decimal
    transaction_count: int
    included_transaction_ids: tuple[str, ...]
    directions: tuple[Direction, ...]
    status: ResultStatus
    warnings: tuple[str, ...] = ()
@dataclass(frozen=True, slots=True)
class CategoryAnalysis:
    """Structured result of the category-analysis capability.

    ``category_totals`` is ordered deterministically (total descending, then
    category name ascending). Expenses without a category are visible through
    the ``uncovered_*`` fields rather than hidden, so category totals may be
    reconciled against ``total_spending``.
    """

    period: Period
    currency: str
    total_spending: Decimal
    category_totals: tuple[CategoryTotal, ...]
    uncovered_amount: Decimal
    uncovered_transaction_count: int
    uncovered_transaction_ids: tuple[str, ...]
    status: ResultStatus
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MerchantTotal:
    """One merchant's spending contribution with its evidence references."""

    merchant: str
    total: Decimal
    transaction_count: int
    transaction_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MerchantAnalysis:
    """Structured result of the merchant/contributor analysis.

    ``merchants`` is ordered deterministically (total descending, then merchant
    name ascending). Expenses without a merchant value are visible through the
    ``unattributed_*`` fields.
    """

    period: Period
    currency: str
    total_spending: Decimal
    merchants: tuple[MerchantTotal, ...]
    unattributed_amount: Decimal
    unattributed_transaction_count: int
    unattributed_transaction_ids: tuple[str, ...]
    status: ResultStatus
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PeriodComparison:
    """Structured result of the period-comparison capability.

    ``absolute_difference`` is ``total_b - total_a``. ``percentage_difference``
    is ``(total_b - total_a) / total_a * 100`` and is ``None`` when a percentage
    is not meaningful (period A total is zero). ``change_direction`` is one of
    ``"increase"``, ``"decrease"``, ``"no_change"``, or ``"not_computed"``.
    """

    period_a: Period
    period_b: Period
    currency: str
    total_a: Decimal
    total_b: Decimal
    count_a: int
    count_b: int
    absolute_difference: Decimal
    percentage_difference: Decimal | None
    change_direction: str
    status: ResultStatus
    warnings: tuple[str, ...] = ()
    included_transaction_ids_a: tuple[str, ...] = ()
    included_transaction_ids_b: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LargestExpense:
    """One noteworthy (largest) expense with its evidence."""

    rank: int
    transaction_id: str
    date: _dt.date
    description: str
    merchant: str | None
    category: str | None
    amount: Decimal


@dataclass(frozen=True, slots=True)
class NoteworthyAnalysis:
    """Structured result of the noteworthy/largest-expenses capability.

    Baseline rule only: the ``limit`` largest expenses by amount, descending,
    with ties broken by ``transaction_id``. This is not anomaly detection.
    """

    period: Period
    currency: str
    rule: str
    limit: int
    total_spending: Decimal
    transaction_count: int
    largest: tuple[LargestExpense, ...]
    status: ResultStatus
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    """One category's spending contribution with its evidence references."""

    category: str
    total: Decimal
    transaction_count: int
    transaction_ids: tuple[str, ...]