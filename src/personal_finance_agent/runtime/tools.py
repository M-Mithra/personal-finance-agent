"""The action/tool interface to the analytical capabilities.

The agent runtime never calls analytical functions directly. Instead it invokes
them through :func:`execute_tool`, which dispatches by tool name to the matching
capability in :mod:`personal_finance_agent.analytics`. Each tool has a clear
name, a clear input contract (its ``params`` dict), and a deterministic output
structure (an analytical result dataclass).

The five initial tools correspond 1:1 to the five analytical capabilities:

* ``spending_summary``
* ``category_analysis``
* ``period_comparison``
* ``merchant_analysis``
* ``noteworthy_transactions``
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from ..analytics import (
    category_analysis,
    largest_expenses,
    merchant_analysis,
    period_comparison,
    spending_summary,
)
from ..models import (
    CategoryAnalysis,
    MerchantAnalysis,
    NoteworthyAnalysis,
    Period,
    PeriodComparison,
    SpendingSummary,
    Transaction,
)

__all__ = [
    "ToolError",
    "execute_tool",
    "tool_for",
    "TOOLS",
    "_period_for_month",
]


class ToolError(Exception):
    """Raised when a tool cannot be executed (unknown name or bad params)."""


def _period_for_month(year: int, month: int) -> Period:
    """Build a labeled Period for a calendar month (shared helper)."""
    return Period.for_month(year, month)


def _require_period(params: dict[str, Any], key: str = "period") -> Period:
    """Extract and validate a Period from tool params."""
    period = params.get(key)
    if not isinstance(period, Period):
        raise ToolError(f"tool parameter '{key}' must be a Period")
    return period


def _require_sequence(
    params: dict[str, Any], key: str
) -> Sequence[Transaction]:
    """Extract and validate a transaction sequence from tool params."""
    value = params.get(key)
    if not isinstance(value, Sequence):
        raise ToolError(f"tool parameter '{key}' must be a sequence of transactions")
    return value


def _spending_summary(params: dict[str, Any]) -> SpendingSummary:
    return spending_summary(
        transactions=_require_sequence(params, "transactions"),
        period=_require_period(params, "period"),
        currency=params.get("currency"),
    )


def _category_analysis(params: dict[str, Any]) -> CategoryAnalysis:
    return category_analysis(
        transactions=_require_sequence(params, "transactions"),
        period=_require_period(params, "period"),
        currency=params.get("currency"),
    )


def _period_comparison(params: dict[str, Any]) -> PeriodComparison:
    return period_comparison(
        transactions=_require_sequence(params, "transactions"),
        period_a=_require_period(params, "period_a"),
        period_b=_require_period(params, "period_b"),
        currency=params.get("currency"),
    )


def _merchant_analysis(params: dict[str, Any]) -> MerchantAnalysis:
    return merchant_analysis(
        transactions=_require_sequence(params, "transactions"),
        period=_require_period(params, "period"),
        currency=params.get("currency"),
    )


def _noteworthy_transactions(params: dict[str, Any]) -> NoteworthyAnalysis:
    limit = params.get("limit", 5)
    return largest_expenses(
        transactions=_require_sequence(params, "transactions"),
        period=_require_period(params, "period"),
        limit=int(limit),
        currency=params.get("currency"),
    )


TOOLS: dict[str, Callable[[dict[str, Any]], object]] = {
    "spending_summary": _spending_summary,
    "category_analysis": _category_analysis,
    "period_comparison": _period_comparison,
    "merchant_analysis": _merchant_analysis,
    "noteworthy_transactions": _noteworthy_transactions,
}


def tool_for(name: str) -> Callable[[dict[str, Any]], object]:
    """Return the tool callable registered under ``name``."""
    if name not in TOOLS:
        raise ToolError(
            f"unknown tool '{name}'; supported: {sorted(TOOLS)}"
        )
    return TOOLS[name]


def execute_tool(
    name: str, params: dict[str, Any]
) -> object:
    """Execute the named tool with ``params`` and return its result.

    Raises :class:`ToolError` when the tool is unknown or a required parameter
    is missing/invalid. Any exception raised by the underlying analytical
    capability is propagated so the runtime can record it as an observation
    error.
    """
    return tool_for(name)(params)
