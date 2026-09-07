"""Deterministic verification of analytical results.

Verification independently recomputes an analytical result from the canonical
transactions and the result's own scope metadata (period, currency, direction
rule), then compares every reported number, reference and ordering against the
recomputation. It never trusts the result fields on their own and never uses an
LLM.

Each ``verify_*`` function returns a structured :class:`VerificationResult`:

- ``status == "passed"``: every check agreed with the recomputation;
- ``status == "failed"``: at least one check disagreed (with expected/actual
  diagnostics);
- ``status == "inconclusive"``: the result could not be verified (typically an
  ``error``-status result with no numeric content to check).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from .analytics import _expenses, _scope, _sum_of, percentage_change
from .models import (
    CategoryAnalysis,
    Direction,
    MerchantAnalysis,
    NoteworthyAnalysis,
    Period,
    PeriodComparison,
    ResultStatus,
    SpendingSummary,
    Transaction,
)

__all__ = [
    "CheckResult",
    "VerificationResult",
    "verify_category_analysis",
    "verify_largest_expenses",
    "verify_merchant_analysis",
    "verify_period_comparison",
    "verify_spending_total",
]

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One individual verification check with diagnostics on failure."""

    name: str
    passed: bool
    message: str
    expected: object | None = None
    actual: object | None = None


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Aggregate outcome of verifying one analytical result."""

    target: str
    status: str
    checks: tuple[CheckResult, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    @property
    def failed(self) -> bool:
        return self.status == "failed"

    @property
    def inconclusive(self) -> bool:
        return self.status == "inconclusive"


def _verdict(target: str, checks: Sequence[CheckResult]) -> VerificationResult:
    if any(not check.passed for check in checks):
        return VerificationResult(target=target, status="failed", checks=tuple(checks))
    if not checks:
        return VerificationResult(target=target, status="inconclusive", checks=(), notes=("no checks could be performed",))
    return VerificationResult(target=target, status="passed", checks=tuple(checks))


def _ok(name: str, message: str = "", expected: object | None = None, actual: object | None = None) -> CheckResult:
    return CheckResult(name=name, passed=True, message=message, expected=expected, actual=actual)


def _bad(name: str, message: str, expected: object | None, actual: object | None) -> CheckResult:
    return CheckResult(name=name, passed=False, message=message, expected=expected, actual=actual)


def _inconclusive(target: str, note: str) -> VerificationResult:
    return VerificationResult(target=target, status="inconclusive", checks=(), notes=(note,))


def verify_spending_total(
    summary: SpendingSummary,
    transactions: Sequence[Transaction],
) -> VerificationResult:
    """Independently recompute and check a spending summary."""
    if summary.status is ResultStatus.ERROR:
        return _inconclusive("spending_summary", "result reported an error; nothing to verify")

    recomputed = _recompute_spending(
        transactions, summary.period, summary.directions, summary.currency
    )
    assert recomputed is not None
    total, count, ids = recomputed

    checks = [
        _check_equal("total", summary.total, total, "spending total does not match the recomputed sum"),
        _check_equal("transaction_count", summary.transaction_count, count, "transaction count does not match"),
        _check_equal("included_transaction_ids", summary.included_transaction_ids, ids, "included transaction references do not match"),
        _check_ids_referenced(transactions, summary.included_transaction_ids, "included_transaction_ids"),
    ]
    return _verdict("spending_summary", checks)
    return VerificationResult(target=target, status="inconclusive", checks=(), notes=(note,))
def verify_category_analysis(
    result: CategoryAnalysis,
    transactions: Sequence[Transaction],
) -> VerificationResult:
    """Independently recompute and check a category analysis.

    Recomputation uses the default spending directions (``expense`` only), which
    is the rule used by the category capability in this slice.
    """
    if result.status is ResultStatus.ERROR:
        return _inconclusive("category_analysis", "result reported an error; nothing to verify")

    scoped = _scope(transactions, result.period, result.currency)
    assert scoped is not None
    expenses = _expenses(scoped, (Direction.EXPENSE,))

    by_category: dict[str, list[Transaction]] = {}
    uncovered: list[Transaction] = []
    for transaction in expenses:
        if transaction.category is not None:
            by_category.setdefault(transaction.category, []).append(transaction)
        else:
            uncovered.append(transaction)

    checks: list[CheckResult] = [
        _check_equal(
            "total_spending",
            result.total_spending,
            _sum_of(transaction.amount for transaction in expenses),
            "total spending does not match the recomputed sum",
        )
    ]

    presented = {entry.category: entry for entry in result.category_totals}
    recomputed = {
        category: _sum_of(transaction.amount for transaction in group)
        for category, group in by_category.items()
    }
    if set(presented) != set(recomputed):
        checks.append(
            _bad(
                "category_set",
                "presented categories do not match the recomputed category set",
                sorted(recomputed),
                sorted(presented),
            )
        )

    for category in sorted(set(presented) & set(recomputed)):
        entry = presented[category]
        checks.append(
            _check_equal(
                f"category_total:{category}",
                entry.total,
                recomputed[category],
                f"total for category {category!r} does not match",
            )
        )
        checks.append(
            _check_equal(
                f"category_ids:{category}",
                entry.transaction_ids,
                tuple(sorted(t.transaction_id for t in by_category.get(category, []))),
                f"evidence references for category {category!r} do not match",
            )
        )

    expected_order = [
        category
        for category, _ in sorted(recomputed.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    checks.append(
        _check_equal(
            "category_ordering",
            [entry.category for entry in result.category_totals],
            expected_order,
            "category totals are not ordered by descending total (category name on ties)",
        )
    )

    checks.append(
        _check_equal(
            "uncovered_amount",
            result.uncovered_amount,
            _sum_of(transaction.amount for transaction in uncovered),
            "uncovered amount does not match",
        )
    )
    checks.append(
        _check_equal(
            "uncovered_transaction_ids",
            result.uncovered_transaction_ids,
            tuple(sorted(t.transaction_id for t in uncovered)),
            "uncovered transaction references do not match",
        )
    )
    checks.append(_check_category_reconciliation(result))
    return _verdict("category_analysis", checks)
def verify_merchant_analysis(
    result: MerchantAnalysis,
    transactions: Sequence[Transaction],
) -> VerificationResult:
    """Independently recompute and check a merchant analysis."""
    if result.status is ResultStatus.ERROR:
        return _inconclusive("merchant_analysis", "result reported an error; nothing to verify")

    scoped = _scope(transactions, result.period, result.currency)
    assert scoped is not None
    expenses = _expenses(scoped, (Direction.EXPENSE,))

    by_merchant: dict[str, list[Transaction]] = {}
    unattributed: list[Transaction] = []
    for transaction in expenses:
        if transaction.merchant is not None:
            by_merchant.setdefault(transaction.merchant, []).append(transaction)
        else:
            unattributed.append(transaction)

    checks: list[CheckResult] = [
        _check_equal(
            "total_spending",
            result.total_spending,
            _sum_of(transaction.amount for transaction in expenses),
            "total spending does not match the recomputed sum",
        )
    ]

    presented = {entry.merchant: entry for entry in result.merchants}
    recomputed = {
        merchant: _sum_of(transaction.amount for transaction in group)
        for merchant, group in by_merchant.items()
    }
    if set(presented) != set(recomputed):
        checks.append(
            _bad(
                "merchant_set",
                "presented merchants do not match the recomputed merchant set",
                sorted(recomputed),
                sorted(presented),
            )
        )

    for merchant in sorted(set(presented) & set(recomputed)):
        entry = presented[merchant]
        checks.append(
            _check_equal(
                f"merchant_total:{merchant}",
                entry.total,
                recomputed[merchant],
                f"total for merchant {merchant!r} does not match",
            )
        )
        checks.append(
            _check_equal(
                f"merchant_ids:{merchant}",
                entry.transaction_ids,
                tuple(sorted(t.transaction_id for t in by_merchant.get(merchant, []))),
                f"evidence references for merchant {merchant!r} do not match",
            )
        )

    expected_order = [
        merchant
        for merchant, _ in sorted(recomputed.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    checks.append(
        _check_equal(
            "merchant_ordering",
            [entry.merchant for entry in result.merchants],
            expected_order,
            "merchants are not ordered by descending total (merchant name on ties)",
        )
    )
    checks.append(
        _check_equal(
            "unattributed_amount",
            result.unattributed_amount,
            _sum_of(transaction.amount for transaction in unattributed),
            "unattributed amount does not match",
        )
    )
    checks.append(
        _check_equal(
            "unattributed_transaction_ids",
            result.unattributed_transaction_ids,
            tuple(sorted(t.transaction_id for t in unattributed)),
            "unattributed transaction references do not match",
        )
    )
    checks.append(_check_merchant_reconciliation(result))
    return _verdict("merchant_analysis", checks)
def verify_period_comparison(
    result: PeriodComparison,
    transactions: Sequence[Transaction],
) -> VerificationResult:
    """Independently recompute and check a period comparison."""
    if result.status is ResultStatus.ERROR:
        return _inconclusive("period_comparison", "result reported an error; nothing to verify")

    recomputed_a = _recompute_spending(
        transactions, result.period_a, (Direction.EXPENSE,), result.currency
    )
    recomputed_b = _recompute_spending(
        transactions, result.period_b, (Direction.EXPENSE,), result.currency
    )
    assert recomputed_a is not None and recomputed_b is not None
    total_a, count_a, ids_a = recomputed_a
    total_b, count_b, ids_b = recomputed_b

    expected_percentage = percentage_change(total_a, total_b)
    expected_direction = _derive_change_direction(total_a, total_b)

    checks = [
        _check_equal("total_a", result.total_a, total_a, "period A total does not match"),
        _check_equal("total_b", result.total_b, total_b, "period B total does not match"),
        _check_equal("count_a", result.count_a, count_a, "period A count does not match"),
        _check_equal("count_b", result.count_b, count_b, "period B count does not match"),
        _check_equal(
            "absolute_difference",
            result.absolute_difference,
            total_b - total_a,
            "absolute difference does not equal total_b - total_a",
        ),
        _check_equal(
            "percentage_difference",
            result.percentage_difference,
            expected_percentage,
            "percentage difference does not match",
        ),
        _check_equal(
            "change_direction",
            result.change_direction,
            expected_direction,
            "change direction is inconsistent with the totals",
        ),
        _check_equal(
            "included_transaction_ids_a",
            result.included_transaction_ids_a,
            ids_a,
            "period A evidence references do not match",
        ),
        _check_equal(
            "included_transaction_ids_b",
            result.included_transaction_ids_b,
            ids_b,
            "period B evidence references do not match",
        ),
    ]
    return _verdict("period_comparison", checks)
def verify_largest_expenses(
    result: NoteworthyAnalysis,
    transactions: Sequence[Transaction],
) -> VerificationResult:
    """Independently recompute and check the largest-expenses result."""
    if result.status is ResultStatus.ERROR:
        return _inconclusive("largest_expenses", "result reported an error; nothing to verify")

    scoped = _scope(transactions, result.period, result.currency)
    assert scoped is not None
    expenses = _expenses(scoped, (Direction.EXPENSE,))
    ranked = sorted(expenses, key=lambda t: (-t.amount, t.transaction_id))
    top = ranked[: result.limit]

    checks: list[CheckResult] = [
        _check_equal(
            "limit_positive",
            result.limit >= 1,
            True,
            "limit must be at least 1",
        ),
        _check_equal(
            "top_length",
            len(result.largest),
            min(len(expenses), result.limit),
            "number of returned expenses does not match the top-N window",
        ),
        _check_equal(
            "rule",
            bool(result.rule.strip()),
            True,
            "rule must describe the deterministic largest-expense rule",
        ),
        _check_equal(
            "transaction_count",
            result.transaction_count,
            len(expenses),
            "transaction count does not match",
        ),
        _check_equal(
            "total_spending",
            result.total_spending,
            _sum_of(transaction.amount for transaction in expenses),
            "total spending does not match",
        ),
        _check_equal(
            "largest_ids",
            tuple(entry.transaction_id for entry in result.largest),
            tuple(transaction.transaction_id for transaction in top),
            "largest-expense references do not match",
        ),
        _check_equal(
            "largest_amounts",
            tuple(entry.amount for entry in result.largest),
            tuple(transaction.amount for transaction in top),
            "largest-expense amounts do not match",
        ),
        _check_equal(
            "ranks",
            tuple(entry.rank for entry in result.largest),
            tuple(range(1, len(top) + 1)),
            "ranks must be sequential starting at 1",
        ),
    ]

    amounts = [entry.amount for entry in result.largest]
    if any(before < after for before, after in zip(amounts, amounts[1:])):
        checks.append(
            _bad(
                "monotonic",
                "largest expenses must be ordered by amount descending",
                "non-increasing amounts",
                amounts,
            )
        )
    else:
        checks.append(_ok("monotonic", "amounts are non-increasing"))

    return _verdict("largest_expenses", checks)


def _check_equal(
    name: str, expected: object, actual: object, message: str
) -> CheckResult:
    if expected == actual:
        return _ok(name, message, expected, actual)
    return _bad(name, message, expected, actual)


def _check_ids_referenced(
    transactions: Sequence[Transaction], ids: tuple[str, ...], label: str
) -> CheckResult:
    known = {transaction.transaction_id for transaction in transactions}
    missing = [transaction_id for transaction_id in ids if transaction_id not in known]
    if missing:
        return _bad(
            label,
            f"evidence references not found in the transaction set: {missing}",
            (),
            ids,
        )
    return _ok(label, "all referenced transactions exist in the supplied set")


def _check_category_reconciliation(result: CategoryAnalysis) -> CheckResult:
    """Category totals plus uncovered spending must reconcile with the total."""
    covered = sum((entry.total for entry in result.category_totals), _ZERO)
    expected = result.total_spending
    actual = covered + result.uncovered_amount
    if actual != expected:
        return _bad(
            "category_reconciliation",
            "category totals plus uncovered spending do not reconcile with total spending",
            expected,
            actual,
        )
    return _ok(
        "category_reconciliation",
        "category totals plus uncovered spending equal total spending",
        expected,
        actual,
    )


def _check_merchant_reconciliation(result: MerchantAnalysis) -> CheckResult:
    """Merchant totals plus unattributed spending must reconcile with the total."""
    attributed = sum((entry.total for entry in result.merchants), _ZERO)
    expected = result.total_spending
    actual = attributed + result.unattributed_amount
    if actual != expected:
        return _bad(
            "merchant_reconciliation",
            "merchant totals plus unattributed spending do not reconcile with total spending",
            expected,
            actual,
        )
    return _ok(
        "merchant_reconciliation",
        "merchant totals plus unattributed spending equal total spending",
        expected,
        actual,
    )


def _recompute_spending(
    transactions: Sequence[Transaction],
    period: Period,
    directions: Sequence[Direction],
    currency: str,
) -> tuple[Decimal, int, tuple[str, ...]] | None:
    scoped = _scope(transactions, period, currency)
    if scoped is None:
        return None
    expenses = _expenses(scoped, directions)
    total = _sum_of(transaction.amount for transaction in expenses)
    return total, len(expenses), tuple(sorted(t.transaction_id for t in expenses))


def _derive_change_direction(total_a: Decimal, total_b: Decimal) -> str:
    if total_b > total_a:
        return "increase"
    if total_b < total_a:
        return "decrease"
    return "no_change"
    return _verdict("largest_expenses", checks)