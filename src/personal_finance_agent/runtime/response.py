"""Deterministic, grounded response generation.

The response generator builds a concise natural-language response from the
structured, verified observations in the agent state. It never independently
calculates financial numbers: every numerical value is read directly from an
analytical result dataclass.
"""

from __future__ import annotations

from decimal import Decimal

from ..models import (
    CategoryAnalysis,
    MerchantAnalysis,
    NoteworthyAnalysis,
    Period,
    PeriodComparison,
    ResultStatus,
    SpendingSummary,
)
from .state import AgentState, Intent, ResponseStatus

__all__ = ["generate_response"]


def _format_amount(amount: Decimal, currency: str) -> str:
    """Format a Decimal amount with its currency code."""
    return f"{currency} {amount:.2f}"


def _period_label(period: Period | None) -> str:
    if period is None or period.label is None:
        return "the period"
    return period.label
def _describe_spending_summary(state: AgentState, obs) -> str:
    result: SpendingSummary = obs.result
    label = _period_label(result.period)
    if result.status is ResultStatus.EMPTY:
        return f"No spending was found for {label}."
    amount = _format_amount(result.total, result.currency)
    return (
        f"Total spending for {label} was {amount} across "
        f"{result.transaction_count} transaction(s)."
    )


def _describe_category_analysis(state: AgentState, obs) -> str:
    result: CategoryAnalysis = obs.result
    label = _period_label(result.period)
    if result.status is ResultStatus.EMPTY:
        return f"No categorized spending was found for {label}."
    total = _format_amount(result.total_spending, result.currency)
    top = result.category_totals[:3]
    parts = [f"Spending for {label} totalled {total}."]
    if top:
        evidence = ", ".join(
            f"{entry.category} {_format_amount(entry.total, result.currency)}"
            for entry in top
        )
        parts.append(f"Top categories: {evidence}.")
    return " ".join(parts)


def _describe_merchant_analysis(state: AgentState, obs) -> str:
    result: MerchantAnalysis = obs.result
    label = _period_label(result.period)
    if result.status is ResultStatus.EMPTY:
        return f"No merchant spending was found for {label}."
    total = _format_amount(result.total_spending, result.currency)
    top = result.merchants[:3]
    parts = [f"Spending for {label} totalled {total}."]
    if top:
        evidence = ", ".join(
            f"{entry.merchant} {_format_amount(entry.total, result.currency)}"
            for entry in top
        )
        parts.append(f"Top merchants: {evidence}.")
    return " ".join(parts)
def _describe_noteworthy(state: AgentState, obs) -> str:
    result: NoteworthyAnalysis = obs.result
    label = _period_label(result.period)
    if result.status is ResultStatus.EMPTY:
        return f"No noteworthy expenses were found for {label}."
    total = _format_amount(result.total_spending, result.currency)
    parts = [f"Spending for {label} totalled {total}. Largest expenses:"]
    for entry in result.largest:
        merchant = entry.merchant or "unknown merchant"
        parts.append(
            f"  {entry.rank}. {_format_amount(entry.amount, result.currency)} "
            f"at {merchant} ({entry.description})"
        )
    return "\n".join(parts)


def _describe_period_comparison(state: AgentState, obs) -> str:
    result: PeriodComparison = obs.result
    if result.status is ResultStatus.EMPTY:
        return "No spending was found in either period to compare."
    label_a = _period_label(result.period_a)
    label_b = _period_label(result.period_b)
    total_a = _format_amount(result.total_a, result.currency)
    total_b = _format_amount(result.total_b, result.currency)
    return (
        f"{label_a}: {total_a}; {label_b}: {total_b}. "
        f"Change: {_format_amount(result.absolute_difference, result.currency)} "
        f"({result.change_direction})."
    )
def _describe_spending_change(state: AgentState) -> str:
    """Build the evidence-based spending-change explanation."""
    comparison_obs = state.observation_for("period_comparison")
    if comparison_obs is None or not comparison_obs.success:
        return "Could not determine the spending change."

    comparison: PeriodComparison = comparison_obs.result
    if comparison.change_direction == "no_change":
        return "Spending did not change meaningfully between the periods."
    if comparison.change_direction == "decrease":
        amount = _format_amount(
            abs(comparison.absolute_difference), comparison.currency
        )
        return f"Spending decreased by {amount} from the earlier period."

    label_b = _period_label(comparison.period_b)
    amount = _format_amount(comparison.absolute_difference, comparison.currency)
    parts = [f"Spending increased by {amount} in {label_b}."]

    cat_obs = state.observation_for("category_analysis")
    if cat_obs is not None and cat_obs.success:
        cat_result: CategoryAnalysis = cat_obs.result
        top_cats = cat_result.category_totals[:3]
        if top_cats:
            evidence = ", ".join(
                f"{entry.category} {_format_amount(entry.total, cat_result.currency)}"
                for entry in top_cats
            )
            parts.append(f"Top category contributors: {evidence}.")

    merch_obs = state.observation_for("merchant_analysis")
    if merch_obs is not None and merch_obs.success:
        merch_result: MerchantAnalysis = merch_obs.result
        top_merch = merch_result.merchants[:3]
        if top_merch:
            evidence = ", ".join(
                f"{entry.merchant} {_format_amount(entry.total, merch_result.currency)}"
                for entry in top_merch
            )
            parts.append(f"Top merchant contributors: {evidence}.")

    return " ".join(parts)
_DESCRIBERS = {
    Intent.SPENDING_SUMMARY: ("spending_summary", _describe_spending_summary),
    Intent.CATEGORY_ANALYSIS: ("category_analysis", _describe_category_analysis),
    Intent.MERCHANT_ANALYSIS: ("merchant_analysis", _describe_merchant_analysis),
    Intent.NOTEWORTHY_TRANSACTIONS: ("noteworthy_transactions", _describe_noteworthy),
    Intent.PERIOD_COMPARISON: ("period_comparison", _describe_period_comparison),
}


def generate_response(state: AgentState) -> str:
    """Generate a grounded response from the agent state."""
    if state.response_status is ResponseStatus.UNSUPPORTED:
        return "I can't handle that request yet."

    if state.response_status is ResponseStatus.AMBIGUOUS:
        return "Your request is ambiguous: no time period was recognized."

    if state.response_status is ResponseStatus.ERROR:
        errors = "; ".join(state.errors) or "unknown error"
        return f"The request could not be completed. Errors: {errors}"

    if state.intent is Intent.SPENDING_CHANGE_EXPLANATION:
        return _describe_spending_change(state)

    entry = _DESCRIBERS.get(state.intent)
    if entry is None:
        return "No response could be generated."

    action_name, describer = entry
    obs = state.observation_for(action_name)
    if obs is None or not obs.success:
        return "No verified result was available to answer the request."

    if not state.verified(action_name):
        return "The analytical result could not be verified."

    return describer(state, obs)
