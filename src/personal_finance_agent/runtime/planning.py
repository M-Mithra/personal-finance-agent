"""Deterministic planner producing structured actions.

The planner maps a recognized intent (with its parsed periods) to an ordered list
of Action objects. It does not execute anything: it only describes what should
be done. Actions are structured, not prose, so the runtime can execute them and
the trajectory remains inspectable.
"""

from __future__ import annotations

from .state import Action, Intent
from .understanding import UnderstandResult

__all__ = ["plan_for", "PLAN_EMPTY", "PLAN_UNSUPPORTED"]

PLAN_EMPTY: tuple[Action, ...] = ()
PLAN_UNSUPPORTED: tuple[Action, ...] = ()
def _first_period(periods):
    """Return the first recognized Period, if any."""
    from ..models import Period

    for item in periods:
        if isinstance(item, Period):
            return item
    return None


def _second_period(periods):
    """Return the second recognized Period, if any."""
    from ..models import Period

    seen = 0
    for item in periods:
        if isinstance(item, Period):
            seen += 1
            if seen == 2:
                return item
    return None
def plan_for(understanding: UnderstandResult) -> tuple[Action, ...]:
    """Return the planned actions for a recognized understanding."""
    intent = understanding.intent
    periods = understanding.periods

    if intent in (Intent.UNSUPPORTED, Intent.AMBIGUOUS):
        return PLAN_EMPTY

    period = _first_period(periods)
    second = _second_period(periods)

    if intent is Intent.SPENDING_SUMMARY:
        if period is None:
            return PLAN_EMPTY
        return (
            Action(
                name="spending_summary",
                params={"period": period},
                purpose="compute total spending for the requested period",
            ),
        )

    if intent is Intent.CATEGORY_ANALYSIS:
        if period is None:
            return PLAN_EMPTY
        return (
            Action(
                name="category_analysis",
                params={"period": period},
                purpose="break spending down by category for the period",
            ),
        )

    if intent is Intent.MERCHANT_ANALYSIS:
        if period is None:
            return PLAN_EMPTY
        return (
            Action(
                name="merchant_analysis",
                params={"period": period},
                purpose="identify top merchants contributing to spending",
            ),
        )

    if intent is Intent.NOTEWORTHY_TRANSACTIONS:
        if period is None:
            return PLAN_EMPTY
        return (
            Action(
                name="noteworthy_transactions",
                params={"period": period, "limit": 5},
                purpose="identify the largest expenses in the period",
            ),
        )

    if intent is Intent.PERIOD_COMPARISON:
        if period is None:
            return PLAN_EMPTY
        target_b = second if second is not None else period
        target_a = period if second is not None else period
        return (
            Action(
                name="period_comparison",
                params={"period_a": target_a, "period_b": target_b},
                purpose="compare spending between two periods",
            ),
        )

    if intent is Intent.SPENDING_CHANGE_EXPLANATION:
        return _plan_spending_change(periods)

    return PLAN_EMPTY
def _plan_spending_change(periods) -> tuple[Action, ...]:
    """Plan the spending-change explanation trajectory."""
    period = _first_period(periods)
    second = _second_period(periods)

    if period is None:
        return PLAN_EMPTY

    if second is not None:
        if second.start < period.start:
            period_a, period_b = second, period
        else:
            period_a, period_b = period, second
        return (
            Action(
                name="period_comparison",
                params={"period_a": period_a, "period_b": period_b},
                purpose="compare spending to detect the change",
            ),
            Action(
                name="category_analysis",
                params={"period": period_b},
                purpose="analyze category contributors to the change",
            ),
            Action(
                name="merchant_analysis",
                params={"period": period_b},
                purpose="analyze merchant contributors to the change",
            ),
        )

    prior = _prior_month(period)
    from ..models import Period

    period_a = Period.for_month(prior.year, prior.month)
    return (
        Action(
            name="period_comparison",
            params={"period_a": period_a, "period_b": period},
            purpose="compare this month spending with the prior month",
        ),
        Action(
            name="category_analysis",
            params={"period": period},
            purpose="analyze category contributors to the change",
        ),
        Action(
            name="merchant_analysis",
            params={"period": period},
            purpose="analyze merchant contributors to the change",
        ),
    )


def _prior_month(period):
    """Return the first day of the month before the period start month."""
    import datetime

    first = period.start
    if first.month == 1:
        return datetime.date(first.year - 1, 12, 1)
    return datetime.date(first.year, first.month - 1, 1)
