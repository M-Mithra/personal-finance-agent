"""Deterministic request understanding.

Maps a user request to one of the supported Intent values (see
docs/04_agent_design.md section 7). This is intentionally transparent and
rule-based: it recognizes the six supported intents plus explicit
UNSUPPORTED and AMBIGUOUS outcomes rather than guessing.

Period parsing is deterministic: a bare month name (e.g. "august") resolves
to that month in the configured default year; explicit "YYYY-MM" or
"month YYYY" forms are also accepted.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field

from .state import Intent, IntentStatus

__all__ = [
    "UnderstandResult",
    "understand",
    "MONTH_NAMES",
    "DEFAULT_YEAR",
    "CATEGORY_SYNONYMS",
    "UNSUPPORTED_KEYWORDS",
]

DEFAULT_YEAR: int = 2025

MONTH_NAMES: dict[str, int] = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

CATEGORY_SYNONYMS: dict[str, str] = {
    "food": "dining",
}

UNSUPPORTED_KEYWORDS: tuple[str, ...] = (
    "tax",
    "investment",
    "credit",
    "loan",
)


@dataclass(frozen=True, slots=True)
class UnderstandResult:
    """Structured outcome of request understanding."""

    intent: Intent = Intent.UNSUPPORTED
    intent_status: IntentStatus = IntentStatus.UNSUPPORTED
    periods: tuple[object, ...] = ()
    detail: str = ""
    warnings: tuple[str, ...] = ()


_INTENT_PATTERNS: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (
        Intent.PERIOD_COMPARISON,
        (
            "compare",
            "comparison",
            "versus",
            " vs ",
            "difference between",
            "month over month",
        ),
    ),
    (
        Intent.CATEGORY_ANALYSIS,
        (
            "categor",
            "breakdown by",
            "spending by category",
            "by category",
            "dining",
            "housing",
            "travel",
            "groceries",
            "transport",
            "utilities",
            "entertainment",
            "shopping",
            "health",
            "subscriptions",
        ),
    ),
    (
        Intent.MERCHANT_ANALYSIS,
        (
            "merchant",
            "contributor",
            "contribute",
            "vendor",
            "store",
            "shop",
            "who did i spend",
            "where did i spend",
            "spent at",
            "spend at",
        ),
    ),
    (
        Intent.NOTEWORTHY_TRANSACTIONS,
        (
            "largest",
            "biggest",
            "most expensive",
            "noteworthy",
            "notable",
            "top expense",
        ),
    ),
    (
        Intent.SPENDING_SUMMARY,
        (
            "spending summary",
            "how much did i spend",
            "total spent",
            "total spending",
            "spending in ",
            "spending for",
            "spend in ",
            "spend on",
            "summary",
            "why was",
        ),
    ),
    (
        Intent.SPENDING_CHANGE_EXPLANATION,
        (
            "why did",
            "what caused",
            "spending change",
            "spending increased",
            "spending decreased",
            "change in spending",
        ),
    ),
)


def _classify_intent(normalized: str) -> Intent:
    """Return the first matching intent, or UNSUPPORTED if none match."""
    for intent, keywords in _INTENT_PATTERNS:
        for keyword in keywords:
            if keyword in normalized:
                return intent
    return Intent.UNSUPPORTED


_MONTH_YEAR_RE = re.compile(r"(\d{4})-(\d{1,2})")
_MONTH_NAME_YEAR_RE = re.compile(
    r"(" + "|".join(MONTH_NAMES.keys()) + r")\s+(\d{4})", re.IGNORECASE
)


def _resolve_period(token: str) -> object | None:
    """Resolve a month reference to a Period, or None if unresolvable."""
    from .tools import _period_for_month

    lowered = token.strip().lower()
    match = _MONTH_YEAR_RE.fullmatch(lowered)
    if match:
        return _period_for_month(int(match.group(1)), int(match.group(2)))
    match = _MONTH_NAME_YEAR_RE.fullmatch(lowered)
    if match:
        month_name = match.group(1).lower()
        return _period_for_month(int(match.group(2)), MONTH_NAMES[month_name])
    if lowered in MONTH_NAMES:
        return _period_for_month(DEFAULT_YEAR, MONTH_NAMES[lowered])
    return None


def _extract_periods(normalized: str) -> tuple[object, ...]:
    """Extract all recognizable month references from the request."""
    periods: list[object] = []
    for match in _MONTH_YEAR_RE.finditer(normalized):
        year, month = int(match.group(1)), int(match.group(2))
        from .tools import _period_for_month

        periods.append(_period_for_month(year, month))
    for match in _MONTH_NAME_YEAR_RE.finditer(normalized):
        month_name = match.group(1).lower()
        year = int(match.group(2))
        from .tools import _period_for_month

        period = _period_for_month(year, MONTH_NAMES[month_name])
        if period not in periods:
            periods.append(period)
    for name, month_number in MONTH_NAMES.items():
        if name in normalized:
            from .tools import _period_for_month

            period = _period_for_month(DEFAULT_YEAR, month_number)
            if period not in periods:
                periods.append(period)
    return tuple(periods)


def _apply_category_synonyms(normalized: str) -> str:
    """Replace category synonyms with canonical category names."""
    for synonym, canonical in CATEGORY_SYNONYMS.items():
        normalized = normalized.replace(synonym, canonical)
    return normalized


def _check_unsupported(normalized: str) -> bool:
    """Return True if the request contains an unsupported keyword."""
    for keyword in UNSUPPORTED_KEYWORDS:
        if keyword in normalized:
            return True
    return False


def understand(request: str) -> UnderstandResult:
    """Determine the intent and relevant periods for a user request."""
    if not request or not request.strip():
        return UnderstandResult(
            intent=Intent.UNSUPPORTED,
            intent_status=IntentStatus.UNSUPPORTED,
            detail="empty request",
        )

    normalized = " " + request.strip().lower() + " "

    if _check_unsupported(normalized):
        return UnderstandResult(
            intent=Intent.UNSUPPORTED,
            intent_status=IntentStatus.UNSUPPORTED,
            detail="unsupported topic",
        )

    normalized = _apply_category_synonyms(normalized)
    intent = _classify_intent(normalized)
    periods = _extract_periods(normalized)

    if intent is Intent.UNSUPPORTED:
        return UnderstandResult(
            intent=intent,
            intent_status=IntentStatus.UNSUPPORTED,
            detail="no supported intent recognized",
        )

    needs_period = intent not in (Intent.UNSUPPORTED, Intent.AMBIGUOUS)
    if needs_period and not periods:
        return UnderstandResult(
            intent=intent,
            intent_status=IntentStatus.AMBIGUOUS,
            periods=periods,
            detail=f"intent '{intent.value}' recognized but no period found",
            warnings=("request mentions no recognizable month",),
        )

    return UnderstandResult(
        intent=intent,
        intent_status=IntentStatus.RECOGNIZED,
        periods=periods,
        detail=f"recognized intent '{intent.value}' with {len(periods)} period(s)",
    )
