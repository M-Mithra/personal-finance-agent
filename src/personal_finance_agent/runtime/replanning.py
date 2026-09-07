"""Bounded follow-up decisions made after observing results.

This is the first place the project demonstrates iterative agent behavior: after
the runtime executes the initial plan and inspects the observations, the
replanning module decides whether more information is required and, if so,
what follow-up actions to add.

The logic is deliberately simple and bounded. For a spending-change explanation,
after observing the period comparison we check whether there is a meaningful
increase in spending; if so, we ensure category and merchant analyses are
planned for the later period. No open-ended loop is introduced.
"""

from __future__ import annotations

from decimal import Decimal

from ..models import Period, PeriodComparison, ResultStatus
from .state import Action, AgentState, Intent, Observation

__all__ = [
    "MEANINGFUL_CHANGE_THRESHOLD",
    "decide_followups",
]

# Minimum absolute change (in the period currency) before we treat a spending
# change as meaningful enough to investigate with category/merchant analysis.
MEANINGFUL_CHANGE_THRESHOLD: Decimal = Decimal("0.01")


def _has_meaningful_increase(comparison: PeriodComparison) -> bool:
    """True when the comparison reports a real increase in spending."""
    if comparison.status is not ResultStatus.SUCCESS:
        return False
    if comparison.change_direction != "increase":
        return False
    return comparison.absolute_difference >= MEANINGFUL_CHANGE_THRESHOLD


def _already_observed(state: AgentState, action_name: str) -> bool:
    """True when an observation for the action already exists."""
    return state.observation_for(action_name) is not None


def _already_pending(state: AgentState, action_name: str, period) -> bool:
    """True when a pending action with the same name and period exists."""
    for action in state.pending_actions:
        if action.name == action_name:
            action_period = action.params.get("period")
            if action_period == period:
                return True
    return False


def decide_followups(state: AgentState) -> list[Action]:
    """Inspect the current state and return any follow-up actions needed.

    For the spending-change explanation intent, after observing a period
    comparison that shows a meaningful increase, ensure category and merchant
    analyses are planned for the later period. Returns an empty list when no
    follow-ups are needed (which is the common case for simple intents).
    """
    if state.intent is not Intent.SPENDING_CHANGE_EXPLANATION:
        return []

    comparison_obs = state.observation_for("period_comparison")
    if comparison_obs is None or not comparison_obs.success:
        return []

    comparison = comparison_obs.result
    if not isinstance(comparison, PeriodComparison):
        return []

    if not _has_meaningful_increase(comparison):
        return []

    period_b = comparison.period_b
    followups: list[Action] = []

    if not _already_observed(state, "category_analysis") and not _already_pending(
        state, "category_analysis", period_b
    ):
        followups.append(
            Action(
                name="category_analysis",
                params={"period": period_b},
                purpose="follow-up: category contributors to the spending increase",
            )
        )

    if not _already_observed(state, "merchant_analysis") and not _already_pending(
        state, "merchant_analysis", period_b
    ):
        followups.append(
            Action(
                name="merchant_analysis",
                params={"period": period_b},
                purpose="follow-up: merchant contributors to the spending increase",
            )
        )

    return followups
