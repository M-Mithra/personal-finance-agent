"""Normalization: validated source records to canonical transactions.

Normalization changes representation without claiming to recover information
that is not there (docs/05_data_design.md section 10): whitespace is collapsed
in display text for comparison, and original source values are preserved so
nothing is silently lost.

The first slice keeps normalization conservative and deterministic:

- ``original_description`` preserves the source value exactly as supplied;
- ``description`` collapses surrounding/internal whitespace for display;
- ``normalized_description`` additionally lower-cases, as a comparison aid only
  (it never merges merchants or categories);
- ``merchant``/``category`` are whitespace-collapsed, or ``None`` when absent
  (category origin becomes ``unresolved`` when absent);
- ``category`` supplied in the source is preserved with origin ``source``;
- ``source_reference`` is carried through for traceability;
- no ML- or LLM-based categorization is applied.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .models import CategoryOrigin, DataQualityStatus, NormalizationStatus, Transaction
from .validation import ParsedRecord

__all__ = ["normalize_record", "normalize_records"]


def normalize_record(parsed: ParsedRecord) -> Transaction:
    """Map one validated source record to a canonical transaction."""
    original_description = parsed.description
    description = _collapse_whitespace(original_description)
    normalized_description = description.lower()

    merchant = _collapse_whitespace(parsed.merchant) if parsed.merchant else None
    category = _collapse_whitespace(parsed.category) if parsed.category else None

    transformed = (
        description != original_description
        or merchant != parsed.merchant
        or category != parsed.category
    )

    return Transaction(
        transaction_id=parsed.transaction_id,
        date=parsed.date,
        amount=parsed.amount,
        direction=parsed.direction,
        currency=parsed.currency,
        description=description,
        merchant=merchant,
        category=category,
        category_origin=(
            CategoryOrigin.SOURCE if category is not None else CategoryOrigin.UNRESOLVED
        ),
        original_description=original_description,
        normalized_description=normalized_description,
        source_reference=parsed.source_reference,
        data_quality_status=DataQualityStatus.USABLE,
        quality_notes=(),
        normalization_status=(
            NormalizationStatus.NORMALIZED
            if transformed
            else NormalizationStatus.AS_SUPPLIED
        ),
    )


def normalize_records(parsed_records: Iterable[ParsedRecord]) -> tuple[Transaction, ...]:
    """Map a sequence of validated records to canonical transactions."""
    return tuple(normalize_record(record) for record in parsed_records)


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())