"""Deterministic analytical capabilities for the Personal Finance Agent.

Every function in this module is pure: it takes canonical transactions and
explicit parameters and returns a structured result dataclass (see ``models.py``).
No function performs interpretation, classification, or any non-deterministic
step. Aggregation uses ``Decimal`` arithmetic only.

Spending semantics (docs/05 sections 7 and 13): a transaction counts as spending
only when its direction is in ``SPENDING_DIRECTIONS`` (by default only
``Direction.EXPENSE``). ``income``, ``transfer`` and ``refund`` transactions are
never silently treated as spending.

Period semantics: periods are inclusive ``[start, end]`` (see ``Period``).
Currencies are never mixed: when ``currency`` is ``None`` and a period contains
multiple currencies, a capability returns an explicit ``ERROR`` result instead
of aggregating incomparable amounts.

All ordering is deterministic: result groups are sorted by descending totals with
ties broken by a stable key, and evidence references are sorted by id.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from .models import (
    CategoryAnalysis,
    CategoryTotal,
    Direction,
    LargestExpense,
    MerchantAnalysis,
    MerchantTotal,
    NoteworthyAnalysis,
    Period,
    PeriodComparison,
    ResultStatus,
    SpendingSummary,
    Transaction,
)

__all__ = [
    "SPENDING_DIRECTIONS",
    "category_analysis",
    "largest_expenses",
    "merchant_analysis",
    "month_period",
    "percentage_change",
    "period_comparison",
    "spending_summary",
    "transactions_in_period",
]

SPENDING_DIRECTIONS: tuple[Direction, ...] = (Direction.EXPENSE,)

_PERCENT_QUANTUM = Decimal("0.01")
_ZERO = Decimal("0")


def month_period(year: int, month: int) -> Period:
    """Explicit labeled period for a calendar month."""
    return Period.for_month(year, month)


def percentage_change(previous: Decimal, current: Decimal) -> Decimal | None:
    """Percent change from ``previous`` to ``current``.

    Returns ``None`` when the percentage is not meaningful (``previous`` is
    zero), so callers can qualify rather than divide by zero.
    """
    if previous == 0:
        return None
    return ((current - previous) / previous * 100).quantize(
        _PERCENT_QUANTUM, rounding=ROUND_HALF_UP
    )


def transactions_in_period(
    transactions: Sequence[Transaction],
    period: Period,
    *,
    currency: str | None = None,
) -> list[Transaction]:
    """Return transactions whose date falls in the inclusive period.

    Raises ``ValueError`` when ``currency`` is ``None`` and the period spans more
    than one currency: mixing currencies would make aggregation meaningless.
    """
    in_period = [
        transaction for transaction in transactions if period.contains(transaction.date)
    ]
    if currency is not None:
        return [
            transaction
            for transaction in in_period
            if transaction.currency.upper() == currency.upper()
        ]
    currencies = {transaction.currency.upper() for transaction in in_period}
    if len(currencies) > 1:
        raise ValueError(
            "period spans multiple currencies; pass an explicit currency to scope "
            f"the selection (currencies: {sorted(currencies)})"
        )
    return in_period


def _scope(
    transactions: Sequence[Transaction],
    period: Period,
    currency: str | None,
) -> list[Transaction] | None:
    """Like :func:`transactions_in_period` but returns ``None`` when ambiguous."""
    in_period = [
        transaction for transaction in transactions if period.contains(transaction.date)
    ]
    if currency is not None:
        return [
            transaction
            for transaction in in_period
            if transaction.currency.upper() == currency.upper()
        ]
    currencies = {transaction.currency.upper() for transaction in in_period}
    if len(currencies) > 1:
        return None
    return in_period


def _result_currency(scoped: list[Transaction], requested: str | None) -> str:
    if requested:
        return requested.upper()
    if scoped:
        return scoped[0].currency.upper()
    return ""


def _sum_of(values: Sequence[Decimal]) -> Decimal:
    total = _ZERO
    for value in values:
        total += value
    return total


def _sorted_ids(transactions: Sequence[Transaction]) -> tuple[str, ...]:
    return tuple(sorted(transaction.transaction_id for transaction in transactions))


def _coerce_directions(
    directions: Sequence[Direction | str],
) -> tuple[Direction, ...]:
    """Normalize caller-supplied direction filters to canonical enum members.

    Strings are matched against :class:`Direction` values case-insensitively so
    callers (and a future agent layer) can pass ``"expense"`` instead of the
    enum member. Unknown values and empty filters raise ``ValueError`` rather
    than silently producing zero results.
    """
    coerced: list[Direction] = []
    for direction in directions:
        if isinstance(direction, Direction):
            coerced.append(direction)
            continue
        candidate = str(direction).strip().lower()
        try:
            coerced.append(Direction(candidate))
        except ValueError:
            valid = ", ".join(member.value for member in Direction)
            raise ValueError(
                f"unknown direction {direction!r}; expected one of: {valid}"
            ) from None
    if not coerced:
        raise ValueError("directions must contain at least one direction")
    return tuple(coerced)


def _expenses(
    scoped: list[Transaction], directions: Sequence[Direction]
) -> list[Transaction]:
    allowed = set(directions)
    return [transaction for transaction in scoped if transaction.direction in allowed]


def spending_summary(
    transactions: Sequence[Transaction],
    period: Period,
    *,
    directions: Sequence[Direction | str] = SPENDING_DIRECTIONS,
    currency: str | None = None,
) -> SpendingSummary:
    """Calculate the total spending within ``period``.

    Returns a structured :class:`SpendingSummary` with an explicit total,
    transaction count, evidence references, currency, direction rule, status and
    warnings. A period with no spending records returns ``status=empty`` with a
    total of zero; an ambiguous multi-currency scope returns ``status=error``.
    """
    directions = _coerce_directions(directions)
    scoped = _scope(transactions, period, currency)
    if scoped is None:
        return SpendingSummary(
            period=period,
            currency="",
            total=_ZERO,
            transaction_count=0,
            included_transaction_ids=(),
            directions=tuple(directions),
            status=ResultStatus.ERROR,
            warnings=(
                "period spans multiple currencies; spending cannot be aggregated",
            ),
        )

    included = _expenses(scoped, directions)
    if not included:
        if not scoped:
            warning = "no transactions found in the period"
        else:
            warning = (
                "no spending transactions found in the period (directions: "
                + ", ".join(sorted(direction.value for direction in directions))
                + ")"
            )
        return SpendingSummary(
            period=period,
            currency=_result_currency(scoped, currency),
            total=_ZERO,
            transaction_count=0,
            included_transaction_ids=(),
            directions=tuple(directions),
            status=ResultStatus.EMPTY,
            warnings=(warning,),
        )

    return SpendingSummary(
        period=period,
        currency=_result_currency(scoped, currency),
        total=_sum_of(transaction.amount for transaction in included),
        transaction_count=len(included),
        included_transaction_ids=_sorted_ids(included),
        directions=tuple(directions),
        status=ResultStatus.SUCCESS,
        warnings=(),
    )


def category_analysis(
    transactions: Sequence[Transaction],
    period: Period,
    *,
    directions: Sequence[Direction | str] = SPENDING_DIRECTIONS,
    currency: str | None = None,
) -> CategoryAnalysis:
    """Group spending by category within ``period``.

    Source categories are preserved as supplied; no categorization is derived.
    Expenses without a category are reported through the ``uncovered_*`` fields.
    """
    directions = _coerce_directions(directions)
    scoped = _scope(transactions, period, currency)
    if scoped is None:
        return CategoryAnalysis(
            period=period,
            currency="",
            total_spending=_ZERO,
            category_totals=(),
            uncovered_amount=_ZERO,
            uncovered_transaction_count=0,
            uncovered_transaction_ids=(),
            status=ResultStatus.ERROR,
            warnings=("period spans multiple currencies; spending cannot be aggregated",),
        )

    included = _expenses(scoped, directions)
    total_spending = _sum_of(transaction.amount for transaction in included)
    if not included:
        return CategoryAnalysis(
            period=period,
            currency=_result_currency(scoped, currency),
            total_spending=_ZERO,
            category_totals=(),
            uncovered_amount=_ZERO,
            uncovered_transaction_count=0,
            uncovered_transaction_ids=(),
            status=ResultStatus.EMPTY,
            warnings=("no spending transactions found in the period",),
        )

    by_category: dict[str, list[Transaction]] = {}
    uncovered: list[Transaction] = []
    for transaction in included:
        if transaction.category is not None:
            by_category.setdefault(transaction.category, []).append(transaction)
        else:
            uncovered.append(transaction)

    grouped: list[tuple[str, list[Transaction], Decimal]] = [
        (category, group, _sum_of(t.amount for t in group))
        for category, group in by_category.items()
    ]
    grouped.sort(key=lambda item: (-item[2], item[0]))

    return CategoryAnalysis(
        period=period,
        currency=_result_currency(scoped, currency),
        total_spending=total_spending,
        category_totals=tuple(
            CategoryTotal(
                category=category,
                total=total,
                transaction_count=len(group),
                transaction_ids=_sorted_ids(group),
            )
            for category, group, total in grouped
        ),
        uncovered_amount=_sum_of(t.amount for t in uncovered),
        uncovered_transaction_count=len(uncovered),
        uncovered_transaction_ids=_sorted_ids(uncovered),
        status=ResultStatus.SUCCESS,
        warnings=(),
    )


def merchant_analysis(
    transactions: Sequence[Transaction],
    period: Period,
    *,
    directions: Sequence[Direction | str] = SPENDING_DIRECTIONS,
    currency: str | None = None,
) -> MerchantAnalysis:
    """Rank merchants/contributors by spending within ``period``.

    Only the source merchant field is used; similar descriptions are never merged.
    Expenses without a merchant value are reported through the
    ``unattributed_*`` fields.
    """
    directions = _coerce_directions(directions)
    scoped = _scope(transactions, period, currency)
    if scoped is None:
        return MerchantAnalysis(
            period=period,
            currency="",
            total_spending=_ZERO,
            merchants=(),
            unattributed_amount=_ZERO,
            unattributed_transaction_count=0,
            unattributed_transaction_ids=(),
            status=ResultStatus.ERROR,
            warnings=("period spans multiple currencies; spending cannot be aggregated",),
        )

    included = _expenses(scoped, directions)
    total_spending = _sum_of(transaction.amount for transaction in included)
    if not included:
        return MerchantAnalysis(
            period=period,
            currency=_result_currency(scoped, currency),
            total_spending=_ZERO,
            merchants=(),
            unattributed_amount=_ZERO,
            unattributed_transaction_count=0,
            unattributed_transaction_ids=(),
            status=ResultStatus.EMPTY,
            warnings=("no spending transactions found in the period",),
        )

    by_merchant: dict[str, list[Transaction]] = {}
    unattributed: list[Transaction] = []
    for transaction in included:
        if transaction.merchant is not None:
            by_merchant.setdefault(transaction.merchant, []).append(transaction)
        else:
            unattributed.append(transaction)

    grouped: list[tuple[str, list[Transaction], Decimal]] = [
        (merchant, group, _sum_of(t.amount for t in group))
        for merchant, group in by_merchant.items()
    ]
    grouped.sort(key=lambda item: (-item[2], item[0]))

    return MerchantAnalysis(
        period=period,
        currency=_result_currency(scoped, currency),
        total_spending=total_spending,
        merchants=tuple(
            MerchantTotal(
                merchant=merchant,
                total=total,
                transaction_count=len(group),
                transaction_ids=_sorted_ids(group),
            )
            for merchant, group, total in grouped
        ),
        unattributed_amount=_sum_of(t.amount for t in unattributed),
        unattributed_transaction_count=len(unattributed),
        unattributed_transaction_ids=_sorted_ids(unattributed),
        status=ResultStatus.SUCCESS,
        warnings=(),
    )


def period_comparison(
    transactions: Sequence[Transaction],
    period_a: Period,
    period_b: Period,
    *,
    directions: Sequence[Direction | str] = SPENDING_DIRECTIONS,
    currency: str | None = None,
) -> PeriodComparison:
    """Compare spending between two explicit periods.

    Both totals are computed independently with identical rules; the difference
    and percentage are derived from those totals. The percentage is ``None`` when
    the period-A total is zero (not meaningful).
    """
    directions = _coerce_directions(directions)
    summary_a = spending_summary(
        transactions, period_a, directions=directions, currency=currency
    )
    summary_b = spending_summary(
        transactions, period_b, directions=directions, currency=currency
    )

    if summary_a.status is ResultStatus.ERROR or summary_b.status is ResultStatus.ERROR:
        return PeriodComparison(
            period_a=period_a,
            period_b=period_b,
            currency="",
            total_a=_ZERO,
            total_b=_ZERO,
            count_a=0,
            count_b=0,
            absolute_difference=_ZERO,
            percentage_difference=None,
            change_direction="not_computed",
            status=ResultStatus.ERROR,
            warnings=("period scope invalid; comparison not computed",),
        )

    total_a, total_b = summary_a.total, summary_b.total
    absolute_difference = total_b - total_a
    percentage = percentage_change(total_a, total_b)
    direction = _change_direction(total_a, total_b)

    warnings: list[str] = []
    warnings.extend(summary_a.warnings)
    warnings.extend(summary_b.warnings)
    if percentage is None and absolute_difference != 0:
        warnings.append(
            "percentage difference not computed because the period A total is zero"
        )
    if total_a == 0 and total_b == 0:
        warnings.append("both period totals are zero")

    status = (
        ResultStatus.EMPTY
        if summary_a.status is ResultStatus.EMPTY
        and summary_b.status is ResultStatus.EMPTY
        else ResultStatus.SUCCESS
    )

    return PeriodComparison(
        period_a=period_a,
        period_b=period_b,
        currency=summary_a.currency or summary_b.currency,
        total_a=total_a,
        total_b=total_b,
        count_a=summary_a.transaction_count,
        count_b=summary_b.transaction_count,
        absolute_difference=absolute_difference,
        percentage_difference=percentage,
        change_direction=direction,
        status=status,
        warnings=tuple(dict.fromkeys(warnings)),
        included_transaction_ids_a=summary_a.included_transaction_ids,
        included_transaction_ids_b=summary_b.included_transaction_ids,
    )


def largest_expenses(
    transactions: Sequence[Transaction],
    period: Period,
    *,
    limit: int = 5,
    directions: Sequence[Direction | str] = SPENDING_DIRECTIONS,
    currency: str | None = None,
) -> NoteworthyAnalysis:
    """Identify the ``limit`` largest expenses within ``period``.

    Baseline deterministic rule only: expenses sorted by amount descending, ties
    broken by ``transaction_id`` ascending. This is deliberately not anomaly
    detection.
    """
    directions = _coerce_directions(directions)
    if limit < 1:
        raise ValueError("limit must be >= 1")

    rule = f"largest {limit} expense(s) by amount, descending; ties broken by transaction_id"
    scoped = _scope(transactions, period, currency)
    if scoped is None:
        return NoteworthyAnalysis(
            period=period,
            currency="",
            rule=rule,
            limit=limit,
            total_spending=_ZERO,
            transaction_count=0,
            largest=(),
            status=ResultStatus.ERROR,
            warnings=("period spans multiple currencies; spending cannot be aggregated",),
        )

    included = _expenses(scoped, directions)
    if not included:
        return NoteworthyAnalysis(
            period=period,
            currency=_result_currency(scoped, currency),
            rule=rule,
            limit=limit,
            total_spending=_ZERO,
            transaction_count=0,
            largest=(),
            status=ResultStatus.EMPTY,
            warnings=("no spending transactions found in the period",),
        )

    ranked = sorted(included, key=lambda t: (-t.amount, t.transaction_id))[:limit]
    largest = tuple(
        LargestExpense(
            rank=index,
            transaction_id=transaction.transaction_id,
            date=transaction.date,
            description=transaction.description,
            merchant=transaction.merchant,
            category=transaction.category,
            amount=transaction.amount,
        )
        for index, transaction in enumerate(ranked, start=1)
    )

    return NoteworthyAnalysis(
        period=period,
        currency=_result_currency(scoped, currency),
        rule=rule,
        limit=limit,
        total_spending=_sum_of(transaction.amount for transaction in included),
        transaction_count=len(included),
        largest=largest,
        status=ResultStatus.SUCCESS,
        warnings=(),
    )


def _change_direction(total_a: Decimal, total_b: Decimal) -> str:
    if total_b > total_a:
        return "increase"
    if total_b < total_a:
        return "decrease"
    return "no_change"