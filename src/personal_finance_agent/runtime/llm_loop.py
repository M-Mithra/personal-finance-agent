"""LLM-driven agent execution loop.

Implements the bounded LLM-driven runtime path approved in DEC-023. The
LLM proposes tool calls or a final response; this runtime validates every
proposal, executes only known tools via :mod:`.tools`, records
observations and independent verification results in ``AgentState``, and
enforces budgets and grounding. The deterministic ``run()`` path is
untouched and remains the default.

Architectural invariants (see docs/10_llm_integration_design.md):

* the runtime controls the loop; the LLM only proposes;
* tool calls are structurally, contractually and semantically validated;
* deterministic analytical tools remain authoritative;
* verification is independent of the model and cannot be overridden;
* raw transactions are never placed into model context;
* no chain-of-thought or private reasoning traces are stored;
* final responses are drafts gated by an MVP monetary-figure grounding
  check against verified evidence (not a semantic claim verifier).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import TYPE_CHECKING, Sequence

from ..analytics import (
    category_analysis,
    largest_expenses,
    merchant_analysis,
    period_comparison,
    spending_summary,
)
from ..llm import (
    LLMClient,
    LLMError,
    LLMRequest,
    ModelResponse,
    ToolCall,
    tool_definition_for,
    validate_model_response,
)
from ..llm.errors import InvalidModelResponseError, MalformedModelResponseError
from ..llm.tool_definitions import DEFAULT_TOOL_DEFINITIONS
from ..llm.types import RESPONSE_TYPE_FINAL, RESPONSE_TYPE_TOOL_CALL
from ..models import Period, Transaction
from . import checks, response as response_module
from .checks import verify_for
from .planning import plan_for
from .state import (
    AgentState,
    Intent,
    IntentStatus,
    Observation,
    ResponseStatus,
    TrajectoryStage,
    VerificationRecord,
)
from .tools import ToolError, execute_tool, TOOLS
from .understanding import understand

if TYPE_CHECKING:  # pragma: no cover
    pass

__all__ = [
    "LLMLoopConfig",
    "LLMTerminationReason",
    "ToolCallValidation",
    "GroundingResult",
    "build_llm_request",
    "grounding_gate",
    "run_llm_loop",
    "summarise_observation_for_llm",
    "validate_llm_tool_call",
]

_SYSTEM_INSTRUCTION = (
    "You are the reasoning component of a personal-finance analysis agent. "
    "You propose ONE action per turn: either call exactly one of the listed "
    "analysis tools with structured arguments, or produce the final answer. "
    "Never compute financial figures yourself; the deterministic tools "
    "produce all numbers. Use only returned evidence in your final answer "
    "and mark interpretations as interpretations."
)

_PERIOD_PATTERN = re.compile(r"^\d{4}-\d{2}$")

# Monetary figures are only treated as financial claims when they appear as
# currency-anchored amounts (e.g. "USD 400.00", "$400", "400.00 USD"). Bare
# numbers such as years ("2025"), month fragments ("08"), or counts ("3")
# are not monetary claims and must not trip the grounding gate. This keeps
# the MVP gate narrow: unsupported *monetary* figures must not be presented
# as established financial facts.
_CURRENCY_PREFIX_PATTERN = re.compile(
    r"(?<!\w)(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|INR|CNY|\$|€|£|¥|₹)\s*(-?[\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)
_CURRENCY_SUFFIX_PATTERN = re.compile(
    r"(?<!\w)(-?[\d,]+(?:\.\d+)?)\s*(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|INR|CNY|dollars?|bucks)",
    re.IGNORECASE,
)

# Instructions appended to the system prompt at different points in the loop.
_FINAL_INSTRUCTION = (
    "If you have enough verified evidence to answer the user's request, "
    "produce a final_response with your answer. Base every monetary figure "
    "only on the verified observations above; mark interpretations as "
    "interpretations. Do not invent numbers."
)

_RETRY_INSTRUCTION = (
    "Your previous proposal was invalid and will not be executed. Review "
    "the tool definitions and the arguments you provided, then propose "
    "exactly one valid tool call or a final response. Do not repeat the "
    "same invalid proposal."
)


class LLMTerminationReason(str, Enum):
    """Why the LLM-driven loop stopped."""

    BUDGET_STEPS = "budget_steps"
    BUDGET_TOOL_CALLS = "budget_tool_calls"
    MAX_CONSECUTIVE_REPEATS = "max_consecutive_repeats"
    MODEL_ERROR = "model_error"
    MAX_RETRIES_INVALID = "max_retries_invalid"
    GROUNDING_FALLBACK = "grounding_fallback"
    RESPONSE_COMPLETE = "response_complete"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"


@dataclass(slots=True)
class LLMLoopConfig:
    """Bounds for the LLM-driven loop (DEC-023).

    All bounds are mandatory and enforced by :func:`run_llm_loop`. The
    defaults match the DEC-023 baseline.
    """

    max_model_steps: int = 6
    max_tool_calls: int = 4
    max_consecutive_repeats: int = 2
    retry_invalid: int = 1

    def __post_init__(self) -> None:
        if self.max_model_steps < 1:
            raise ValueError("max_model_steps must be >= 1")
        if self.max_tool_calls < 1:
            raise ValueError("max_tool_calls must be >= 1")
        if self.max_consecutive_repeats < 1:
            raise ValueError("max_consecutive_repeats must be >= 1")
        if self.retry_invalid < 0:
            raise ValueError("retry_invalid must be >= 0")


@dataclass(slots=True)
class ToolCallValidation:
    """Outcome of validating one model-proposed tool call.

    Validation runs through three layers in order — structural, contract,
    semantic — and the first failing layer determines the outcome. A fully
    valid proposal records ``layer == "ok"``.
    """

    passed: bool
    layer: str
    reason: str
    tool_name: str



# ---------------------------------------------------------------------------
# Private helpers for validation
# ---------------------------------------------------------------------------

class _CoercionError(ValueError):
    """Internal signal that model arguments cannot be coerced to a runnable form."""


class _InvalidProposalError(ValueError):
    """Internal signal that a tool call failed validation (retryable)."""


def _coerce_period_value(value: object) -> Period:
    """Coerce an LLM-provided period value into a Period.

    Accepted forms: a Period instance, a YYYY-MM string, or a
    (year, month) tuple/list pair. Anything else raises _CoercionError.
    """
    from .tools import _period_for_month

    if isinstance(value, Period):
        return value
    if isinstance(value, str):
        text = value.strip()
        if _PERIOD_PATTERN.fullmatch(text):
            year = int(text[0:4])
            month = int(text[5:7])
            if not 1 <= month <= 12:
                raise _CoercionError(f"month out of range in period {value!r}")
            try:
                return _period_for_month(year, month)
            except ValueError as exc:
                raise _CoercionError(str(exc)) from exc
        raise _CoercionError(
            f"period string must use YYYY-MM form; got {value!r}"
        )
    if isinstance(value, (tuple, list)) and len(value) == 2:
        year, month = value
        if isinstance(year, bool) or isinstance(month, bool):
            raise _CoercionError(f"invalid (year, month) pair: {value!r}")
        if not isinstance(year, int) or not isinstance(month, int):
            raise _CoercionError(f"invalid (year, month) pair: {value!r}")
        if not 1 <= month <= 12:
            raise _CoercionError(f"month out of range in period {value!r}")
        try:
            return _period_for_month(year, month)
        except ValueError as exc:
            raise _CoercionError(str(exc)) from exc
    raise _CoercionError(
        f"period must be a Period, YYYY-MM string, or (year, month); got {value!r}"
    )


def _require_period(value: object, *, label: str = "period") -> Period:
    """Validate/coerce one period argument for the semantic layer."""
    try:
        return _coerce_period_value(value)
    except _CoercionError:
        raise
    except (ValueError, TypeError) as exc:
        raise _CoercionError(f"invalid {label}: {exc}") from exc


def _require_int(
    value: object, *, label: str, min_value: int = 1, max_value: int | None = None
) -> int:
    """Validate one integer argument for the semantic layer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise _CoercionError(f"{label} must be an integer; got {value!r}")
    if value < min_value:
        raise _CoercionError(f"{label} must be >= {min_value}; got {value!r}")
    if max_value is not None and value > max_value:
        raise _CoercionError(f"{label} must be <= {max_value}; got {value!r}")
    return value


def _require_amount(value: object, *, label: str = "amount"):
    """Validate one non-negative numeric argument for the semantic layer."""
    if isinstance(value, bool):
        raise _CoercionError(f"{label} must be a non-negative number; got {value!r}")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise _CoercionError(f"{label} must be a number; got {value!r}") from exc
    if amount < 0:
        raise _CoercionError(f"{label} must be non-negative; got {value!r}")
    return amount


class _MissingKey(KeyError):
    """A required tool argument was absent from the model's proposal."""


@dataclass(frozen=True, slots=True)
class _SemanticBoundary:
    """Where a semantic check failed, if it did."""

    tool_name: str
    reason: str



# ---------------------------------------------------------------------------
# Contract helpers
# ---------------------------------------------------------------------------


_DateLike = tuple[int, int]


# ---------------------------------------------------------------------------
# Observation summarisation for model context
# ---------------------------------------------------------------------------


def summarise_observation_for_llm(
    observation: Observation,
) -> dict[str, object]:
    """Summarise one observation for inclusion in an LLM request.

    Observations are reduced to structured metadata: the action name, whether
    it succeeded, and a compact summary of the result or error. Raw transaction
    data is never surfaced to the model.
    """
    summary: dict[str, object] = {
        "action_name": observation.action_name,
        "success": observation.success,
    }
    if observation.success and observation.result is not None:
        summary["result_summary"] = _summarise_result(observation.result)
    elif observation.error is not None:
        summary["error"] = observation.error
    else:
        summary["result_summary"] = None
    return summary


def _summarise_result(result: object) -> dict[str, object]:
    """Build a compact, model-facing summary of an analytical result."""
    from ..models import (
        CategoryAnalysis,
        MerchantAnalysis,
        NoteworthyAnalysis,
        PeriodComparison,
        SpendingSummary,
    )

    if isinstance(result, SpendingSummary):
        return {
            "type": "spending_summary",
            "status": result.status.value,
            "total": str(result.total),
            "currency": result.currency,
            "transaction_count": result.transaction_count,
            "period_label": result.period.label,
        }
    if isinstance(result, CategoryAnalysis):
        return {
            "type": "category_analysis",
            "status": result.status.value,
            "total_spending": str(result.total_spending),
            "currency": result.currency,
            "period_label": result.period.label,
            "category_count": len(result.category_totals),
            "top_categories": [
                {"category": entry.category, "total": str(entry.total)}
                for entry in result.category_totals[:5]
            ],
        }
    if isinstance(result, PeriodComparison):
        return {
            "type": "period_comparison",
            "status": result.status.value,
            "period_a_label": result.period_a.label,
            "period_b_label": result.period_b.label,
            "total_a": str(result.total_a),
            "total_b": str(result.total_b),
            "absolute_difference": str(result.absolute_difference),
            "percentage_difference": (
                str(result.percentage_difference)
                if result.percentage_difference is not None
                else None
            ),
            "change_direction": result.change_direction,
            "currency": result.currency,
        }
    if isinstance(result, MerchantAnalysis):
        return {
            "type": "merchant_analysis",
            "status": result.status.value,
            "total_spending": str(result.total_spending),
            "currency": result.currency,
            "period_label": result.period.label,
            "merchant_count": len(result.merchants),
            "top_merchants": [
                {"merchant": entry.merchant, "total": str(entry.total)}
                for entry in result.merchants[:5]
            ],
        }
    if isinstance(result, NoteworthyAnalysis):
        return {
            "type": "noteworthy_transactions",
            "status": result.status.value,
            "period_label": result.period.label,
            "currency": result.currency,
            "largest_count": len(result.largest),
            "largest": [
                {
                    "rank": entry.rank,
                    "transaction_id": entry.transaction_id,
                    "amount": str(entry.amount),
                    "merchant": entry.merchant,
                    "description": entry.description,
                }
                for entry in result.largest[:5]
            ],
        }
    return {"type": "unknown", "note": "result type not recognised by LLM context"}


# ---------------------------------------------------------------------------
# Verification summary for model context
# ---------------------------------------------------------------------------


def _summarise_verification(
    record: VerificationRecord,
) -> dict[str, object]:
    """Summarise one verification record for model context."""
    summary: dict[str, object] = {
        "action_name": record.action_name,
        "trust": record.trust,
        "status": record.status,
    }
    if record.detail is not None:
        summary["checks_passed"] = getattr(
            record.detail, "passed", None
        )
        summary["checks_failed"] = getattr(
            record.detail, "failed", None
        )
        summary["checks_inconclusive"] = getattr(
            record.detail, "inconclusive", None
        )
    return summary


# ---------------------------------------------------------------------------
# Build an LLM request from agent state and loop context
# ---------------------------------------------------------------------------


def build_llm_request(
    user_request: str,
    state: AgentState,
    observation_summaries: list[dict[str, object]],
    verification_summaries: list[dict[str, object]],
    completed_tool_names: list[str],
    config: LLMLoopConfig | None = None,
) -> LLMRequest:
    """Build a provider-neutral LLM request from the current agent state.

    The request carries:

    * the original user request;
    * the interpreted intent (if any);
    * tool definitions for the five analytical tools;
    * structured observation summaries (never raw transactions);
    * verification summaries showing which results were verified, failed, or
      inconclusive;
    * the names of tools already executed (so the model can avoid repeats);
    * a system instruction appropriate to the current loop stage;
    * a compact state summary for budget awareness.
    """
    instruction = _SYSTEM_INSTRUCTION
    if state.intent is not None and state.intent != Intent.UNSUPPORTED:
        instruction = instruction + " "
        instruction = (
            instruction
            + f"The interpreted intent for this request is '{state.intent.value}'. "
            + "You must follow this intent and must not override it."
        )

    request = LLMRequest(
        user_request=user_request,
        intent=None
        if state.intent is None or state.intent == Intent.UNSUPPORTED
        else state.intent.value,
        tool_definitions=tuple(DEFAULT_TOOL_DEFINITIONS),
        observations=tuple(observation_summaries),
        verification=tuple(verification_summaries),
        conversation=(),
        system_instruction=instruction,
        state_summary={
            "periods": [
                p.label if isinstance(p, Period) else str(p)
                for p in state.periods
            ],
            "completed_actions": list(state.completed_actions),
            "llm_steps_used": state.llm_steps_used,
            "tool_calls_used": state.tool_calls_used,
            "model_identifier": state.model_identifier,
        },
        extra={
            "completed_tool_names": completed_tool_names,
            "max_model_steps": config.max_model_steps
            if config is not None
            else LLMLoopConfig.max_model_steps,
            "max_tool_calls": config.max_tool_calls
            if config is not None
            else LLMLoopConfig.max_tool_calls,
            "max_consecutive_repeats": (
                config.max_consecutive_repeats
                if config is not None
                else LLMLoopConfig.max_consecutive_repeats
            ),
        },
    )
    return request


# ---------------------------------------------------------------------------
# Tool call validation
# ---------------------------------------------------------------------------


_VALID_TOOL_NAMES = frozenset(TOOLS.keys())


def validate_llm_tool_call(
    call: ToolCall,
) -> ToolCallValidation:
    """Validate one model-proposed tool call through three layers.

    Layers (first failure wins):

    1. **structural** — name is a non-empty string; arguments is a dict.
    2. **contract** — tool exists in the registered tool set; argument names,
       types, and requiredness match the tool definition.
    3. **semantic** — argument values are semantically valid (dates parseable,
       integers within bounds, amounts non-negative, periods within a sane
       range).

    Returns a :class:`ToolCallValidation` whose ``layer`` is ``"ok"`` when
    every layer passed.
    """
    if not isinstance(call, ToolCall):
        return ToolCallValidation(
            passed=False,
            layer="structural",
            reason=f"tool call is not a ToolCall: {type(call).__name__}",
            tool_name="",
        )

    name = call.name
    arguments = call.arguments

    # --- Layer 1: structural -------------------------------------------------
    if not isinstance(name, str) or not name.strip():
        return ToolCallValidation(
            passed=False,
            layer="structural",
            reason="tool call name must be a non-empty string",
            tool_name=name if isinstance(name, str) else "",
        )
    if not isinstance(arguments, dict):
        return ToolCallValidation(
            passed=False,
            layer="structural",
            reason="tool call arguments must be a structured mapping, not free-form text",
            tool_name=name,
        )

    tool_name = name.strip()
    definition = tool_definition_for(tool_name)
    if definition is None:
        return ToolCallValidation(
            passed=False,
            layer="contract",
            reason=(
                f"unknown tool '{tool_name}'; supported: {sorted(_VALID_TOOL_NAMES)}"
            ),
            tool_name=tool_name,
        )

    # --- Layer 2: contract --------------------------------------------------
    required_args = {a.name for a in definition.arguments if a.required}
    provided_keys = set(arguments.keys())
    missing = sorted(required_args - provided_keys)
    if missing:
        return ToolCallValidation(
            passed=False,
            layer="contract",
            reason=(
                f"tool '{tool_name}' is missing required arguments: {missing}"
            ),
            tool_name=tool_name,
        )

    unexpected = sorted(provided_keys - {a.name for a in definition.arguments})
    if unexpected:
        return ToolCallValidation(
            passed=False,
            layer="contract",
            reason=(
                f"tool '{tool_name}' received unexpected arguments: {unexpected}"
            ),
            tool_name=tool_name,
        )

    # --- Layer 3: semantic --------------------------------------------------
    semantic_boundary = _validate_tool_arguments_semantically(
        tool_name, arguments, definition
    )
    if semantic_boundary is not None:
        return ToolCallValidation(
            passed=False,
            layer="semantic",
            reason=semantic_boundary.reason,
            tool_name=tool_name,
        )

    return ToolCallValidation(
        passed=True,
        layer="ok",
        reason="",
        tool_name=tool_name,
    )


def _validate_tool_arguments_semantically(
    tool_name: str,
    arguments: dict[str, object],
    definition: ToolDefinition,
) -> _SemanticBoundary | None:
    """Run semantic validation for one tool call's arguments.

    Returns a :class:`_SemanticBoundary` when a check fails, or ``None`` when
    all arguments are semantically acceptable. This is the MVP semantic layer:
    it checks types, ranges, and parseability; it does **not** attempt to
    interpret business rules or verify claim truthfulness.
    """
    for arg in definition.arguments:
        if arg.name not in arguments:
            continue
        value = arguments[arg.name]
        boundary = _check_argument_semantically(tool_name, arg, value)
        if boundary is not None:
            return boundary
    # Cross-argument rule (DEC-023): period_comparison requires
    # period_a <= period_b. Reversed periods are rejected deterministically
    # at the semantic layer (not normalized), so the model receives an
    # explicit invalid-proposal signal and can retry with corrected order.
    if tool_name == "period_comparison":
        if "period_a" in arguments and "period_b" in arguments:
            try:
                period_a = _coerce_period_value(arguments["period_a"])
                period_b = _coerce_period_value(arguments["period_b"])
            except (_CoercionError, ValueError, TypeError):
                return None  # individual argument check already reported it
            if period_a.start > period_b.start:
                return _SemanticBoundary(
                    tool_name=tool_name,
                    reason=(
                        "period_a must not start after period_b "
                        f"(reversed periods: {arguments['period_a']!r} > "
                        f"{arguments['period_b']!r}); swap them so period_a "
                        "is the earlier period"
                    ),
                )
    return None


def _check_argument_semantically(
    tool_name: str,
    arg: ToolArgumentSchema,
    value: object,
) -> _SemanticBoundary | None:
    """Check one argument value for semantic validity."""
    if arg.type == "Period":
        try:
            _require_period(value, label=arg.name)
        except (_CoercionError, ValueError, TypeError) as exc:
            return _SemanticBoundary(
                tool_name=tool_name,
                reason=f"argument '{arg.name}' must be a valid period (YYYY-MM or (year, month)); got {value!r}: {exc}",
            )
        return None

    if arg.type == "int":
        try:
            _require_int(
                value,
                label=arg.name,
                min_value=1,
                max_value=None,
            )
        except (_CoercionError, ValueError) as exc:
            return _SemanticBoundary(
                tool_name=tool_name,
                reason=f"argument '{arg.name}' must be a positive integer; got {value!r}: {exc}",
            )
        return None

    if arg.type == "Decimal" or arg.type == "amount":
        try:
            _require_amount(value, label=arg.name)
        except (_CoercionError, ValueError) as exc:
            return _SemanticBoundary(
                tool_name=tool_name,
                reason=f"argument '{arg.name}' must be a non-negative number; got {value!r}: {exc}",
            )
        return None

    # Unknown types are not semantically validated here; contract layer already
    # checked that the name is legitimate.
    return None


def _coerce_tool_args_for_execution(
    tool_name: str, arguments: dict[str, object]
) -> dict[str, object]:
    """Coerce LLM arguments into the runnable tool contract.

    Period-typed arguments (``period``, ``period_a``, ``period_b``) may arrive
    as ``YYYY-MM`` strings or ``(year, month)`` pairs; they are coerced to
    :class:`Period` objects via :func:`_coerce_period_value`. All other
    arguments pass through unchanged. Raises :class:`_CoercionError` when a
    declared period argument cannot be coerced.
    """
    from ..llm.tool_definitions import tool_definition_for as _definition_for

    definition = _definition_for(tool_name)
    if definition is None:
        return dict(arguments)
    period_arg_names = {a.name for a in definition.arguments if a.type == "Period"}
    coerced = dict(arguments)
    for name in period_arg_names:
        if name in coerced:
            coerced[name] = _coerce_period_value(coerced[name])
    return coerced


def _repeat_key(arguments: dict[str, object]) -> str:
    """Build a deterministic key for identical-repeat detection.

    ``transactions`` are excluded (injected by the runtime, identical every
    time). Period objects are reduced to their label/boundaries; everything
    else uses ``repr``.
    """
    parts: list[str] = []
    for key in sorted(arguments.keys()):
        if key == "transactions":
            continue
        value = arguments[key]
        if isinstance(value, Period):
            parts.append(f"{key}={value.label or (value.start.isoformat(), value.end.isoformat())}")
        else:
            parts.append(f"{key}={value!r}")
    return "|".join(parts)


def _consume_matching_pending_action(state: AgentState, tool_name: str) -> bool:
    """Remove the first pending action with ``tool_name`` (by name).

    Returns True when an action was consumed. Name-only matching is the MVP
    rule: model proposals carry YYYY-MM strings while the deterministic plan
    carries Period objects, so strict argument equality would never match and
    the runtime would duplicate planned evidence after every model call.
    """
    for index, action in enumerate(state.pending_actions):
        if action.name == tool_name:
            del state.pending_actions[index]
            return True
    return False


def _with_retry_instruction(request: LLMRequest) -> LLMRequest:
    """Return a copy of ``request`` with the retry instruction appended.

    ``LLMRequest`` is frozen, so retry handling rebuilds the request instead
    of mutating it in place.
    """
    base = request.system_instruction or ""
    return LLMRequest(
        user_request=request.user_request,
        intent=request.intent,
        tool_definitions=request.tool_definitions,
        observations=request.observations,
        verification=request.verification,
        conversation=request.conversation,
        system_instruction=(base + " " + _RETRY_INSTRUCTION).strip(),
        state_summary=dict(request.state_summary),
        extra=dict(request.extra),
    )


# ---------------------------------------------------------------------------
# Grounding gate: MVP monetary-figure cross-check
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GroundingResult:
    """Outcome of the MVP grounding gate on a final-response draft.

    The gate is intentionally narrow: it checks that every monetary figure
    appearing in the draft corresponds to a monetary figure present in the
    verified observations. It is **not** a natural-language claim verifier and
    does not attempt to reason about intent, attribution, or causality.
    """

    passed: bool
    figures_found: list[str]
    figures_verified: list[str]
    figures_unverified: list[str]
    note: str


def grounding_gate(
    draft: str,
    state: AgentState,
) -> GroundingResult:
    """Run the MVP grounding gate on a final-response draft.

    The gate:

    1. Extracts every currency-anchored monetary figure from the draft
       (e.g. "USD 400.00"; bare years/counts are not monetary claims).
    2. Extracts every monetary figure from verified observations in state.
    3. Checks that every draft figure has a corresponding verified figure.

    When the gate passes, the draft is treated as grounded enough for the MVP.
    When it fails, the runtime falls back to the deterministic renderer or a
    safe fallback response.

    This is **currency-anchored figure matching**, not semantic claim
    verification. Interpretations remain the model's responsibility; the gate
    only guards against invented monetary amounts. A correct number attached
    to an incorrect qualitative explanation may still pass.
    """
    if not isinstance(draft, str) or not draft.strip():
        return GroundingResult(
            passed=False,
            figures_found=[],
            figures_verified=[],
            figures_unverified=[],
            note="draft is empty or not a string",
        )

    draft_figures = _extract_monetary_figures(draft)
    if not draft_figures:
        return GroundingResult(
            passed=True,
            figures_found=[],
            figures_verified=[],
            figures_unverified=[],
            note="draft contains no monetary figures to check",
        )

    verified_figures = _collect_verified_figures(state)
    unverified = [
        fig for fig in draft_figures if fig not in verified_figures
    ]

    if unverified:
        return GroundingResult(
            passed=False,
            figures_found=draft_figures,
            figures_verified=[
                fig for fig in draft_figures if fig in verified_figures
            ],
            figures_unverified=unverified,
            note=(
                f"{len(unverified)} monetary figure(s) in the draft have no "
                f"corresponding figure in verified observations: {unverified}"
            ),
        )

    return GroundingResult(
        passed=True,
        figures_found=draft_figures,
        figures_verified=draft_figures,
        figures_unverified=[],
        note="all monetary figures in the draft correspond to verified observations",
    )


def _extract_monetary_figures(text: str) -> list[str]:
    """Extract normalised currency-anchored monetary figures from text.

    Only numbers attached to a currency marker (prefix like ``USD 400.00``
    or suffix like ``400 dollars``) count as monetary claims. Bare numbers
    (years, month fragments, counts) are ignored. Returns the unique set in
    order of first appearance.
    """
    matches: list[str] = []
    seen: set[str] = set()
    for pattern in (_CURRENCY_PREFIX_PATTERN, _CURRENCY_SUFFIX_PATTERN):
        for match in pattern.finditer(text):
            raw = match.group(1)
            try:
                normalised = _normalise_figure(raw)
            except (ValueError, InvalidOperation):
                continue
            if normalised not in seen:
                seen.add(normalised)
                matches.append(normalised)
    return matches


def _normalise_figure(raw: str) -> str:
    """Normalise a matched figure substring to a canonical decimal string."""
    cleaned = raw.replace(",", "")
    d = Decimal(cleaned)
    # Canonical form: up to 2 decimal places, strip trailing zeros.
    s = f"{d:.2f}"
    if s.endswith("0") and not s.endswith(".00"):
        s = s.rstrip("0").rstrip(".") if s.endswith(".") else s
    return s


def _collect_verified_figures(state: AgentState) -> list[str]:
    """Collect every monetary figure from verified observations in state."""
    figures: list[str] = []
    seen: set[str] = set()
    for observation in state.observations:
        if not observation.success:
            continue
        if not state.verified(observation.action_name):
            continue
        if observation.result is None:
            continue
        for figure in _extract_figures_from_result(observation.result):
            if figure not in seen:
                seen.add(figure)
                figures.append(figure)
    return figures


def _extract_figures_from_result(result: object) -> list[str]:
    """Extract monetary figures from an analytical result."""
    from ..models import (
        CategoryAnalysis,
        MerchantAnalysis,
        NoteworthyAnalysis,
        PeriodComparison,
        SpendingSummary,
    )

    candidates: list[object] = []
    if isinstance(result, SpendingSummary):
        candidates.append(result.total)
    elif isinstance(result, CategoryAnalysis):
        candidates.append(result.total_spending)
        for entry in result.category_totals:
            candidates.append(entry.total)
    elif isinstance(result, PeriodComparison):
        candidates.extend(
            [result.total_a, result.total_b, result.absolute_difference]
        )
        if result.percentage_difference is not None:
            candidates.append(result.percentage_difference)
    elif isinstance(result, MerchantAnalysis):
        candidates.append(result.total_spending)
        for entry in result.merchants:
            candidates.append(entry.total)
    elif isinstance(result, NoteworthyAnalysis):
        candidates.append(result.total_spending)
        for entry in result.largest:
            candidates.append(entry.amount)

    figures: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if isinstance(candidate, Decimal):
            normalised = _normalise_figure(str(candidate))
            if normalised not in seen:
                seen.add(normalised)
                figures.append(normalised)
    return figures


# ---------------------------------------------------------------------------
# Deterministic renderer fallback
# ---------------------------------------------------------------------------


def _deterministic_response_from_state(state: AgentState) -> str:
    """Generate a deterministic grounded response from state when the LLM gate
    fails or is not used.

    This reuses the existing deterministic response module so the fallback is
    consistent with the deterministic runtime path.
    """
    return response_module.generate_response(state)


# ---------------------------------------------------------------------------
# The LLM-driven loop
# ---------------------------------------------------------------------------


def run_llm_loop(
    request: str,
    transactions: Sequence[Transaction],
    llm_client: LLMClient,
    config: LLMLoopConfig | None = None,
) -> AgentState:
    """Run the bounded LLM-driven agent loop for one request.

    The loop:

    1. Understands the request deterministically (reuses :func:`understand`).
    2. If the request is unsupported or ambiguous, returns a clarification
       response immediately without calling the model.
    3. Otherwise, enters a bounded loop where the LLM proposes one tool call
       or a final response per step.
    4. Validates every proposal through :func:`validate_model_response` and
       :func:`validate_llm_tool_call`.
    5. On invalid output: one bounded retry; on second consecutive invalid
       output: terminate safely.
    6. Executes valid tool calls through :func:`execute_tool`, records
       observations, runs verification through :func:`verify_for`, and updates
       state.
    7. On final_response: runs the grounding gate; if it passes, returns the
       draft; if it fails, falls back to the deterministic renderer or a safe
       fallback.
    8. Terminates on budget exhaustion, model error, or safe failure.

    The deterministic :func:`run` path is untouched and remains the default;
    this function is opt-in.
    """
    if config is None:
        config = LLMLoopConfig()

    state = AgentState(request=request)
    state.model_identifier = llm_client.model_identifier

    # --- Stage 1: understanding ----------------------------------------------
    understanding = understand(request)
    state.intent = understanding.intent
    state.intent_status = understanding.intent_status
    state.intent_detail = understanding.detail
    state.periods = list(understanding.periods)
    state.assumptions.extend(understanding.warnings)
    state.record(TrajectoryStage.UNDERSTAND, f"understand: {understanding.detail}")

    if understanding.intent_status is IntentStatus.UNSUPPORTED:
        state.response_status = ResponseStatus.UNSUPPORTED
        state.record(
            TrajectoryStage.RESPOND, "respond: unsupported request (clarification)"
        )
        state.termination_reason = LLMTerminationReason.UNSUPPORTED.value
        state.response = (
            "I can't help with that request yet. I can analyse spending by "
            "period, category, merchant, or notable transactions. Could you "
            "rephrase your request in terms of spending analysis?"
        )
        return state

    if understanding.intent_status is IntentStatus.AMBIGUOUS:
        state.response_status = ResponseStatus.AMBIGUOUS
        state.record(
            TrajectoryStage.RESPOND, "respond: ambiguous request (clarification)"
        )
        state.termination_reason = LLMTerminationReason.AMBIGUOUS.value
        state.response = (
            "Your request is ambiguous: no time period was recognized. "
            "Please specify a month (e.g. 'August 2025' or '2025-08')."
        )
        return state

    # --- Stage 2: plan -------------------------------------------------------
    state.record(TrajectoryStage.PLAN, "plan actions (LLM-driven)")
    state.plan = list(plan_for(understanding))
    state.pending_actions = list(state.plan)

    if not state.plan:
        state.response_status = ResponseStatus.INCOMPLETE
        state.errors.append(
            "planner produced no actions for a recognized intent"
        )
        state.record(TrajectoryStage.RESPOND, "respond: empty plan")
        state.termination_reason = LLMTerminationReason.RESPONSE_COMPLETE.value
        state.response = _deterministic_response_from_state(state)
        return state

    # --- Stage 3: bounded LLM loop ------------------------------------------
    consecutive_invalid = 0
    last_invalid_reason = ""
    repeated_calls: dict[str, int] = {}
    observation_summaries: list[dict[str, object]] = []
    verification_summaries: list[dict[str, object]] = []

    while True:
        # Budget checks.
        if state.llm_steps_used >= config.max_model_steps:
            state.termination_reason = LLMTerminationReason.BUDGET_STEPS.value
            state.response_status = ResponseStatus.INCOMPLETE
            state.record(
                TrajectoryStage.ERROR,
                f"model step budget exhausted ({config.max_model_steps})",
            )
            state.response = _deterministic_response_from_state(state)
            return state

        if state.tool_calls_used >= config.max_tool_calls:
            state.termination_reason = LLMTerminationReason.BUDGET_TOOL_CALLS.value
            state.response_status = ResponseStatus.INCOMPLETE
            state.record(
                TrajectoryStage.ERROR,
                f"tool call budget exhausted ({config.max_tool_calls})",
            )
            state.response = _deterministic_response_from_state(state)
            return state

        # Build request (immutable: retry variants are rebuilt per attempt).
        request_obj = build_llm_request(
            user_request=request,
            state=state,
            observation_summaries=observation_summaries,
            verification_summaries=verification_summaries,
            completed_tool_names=list(state.completed_actions),
            config=config,
        )

        # Append appropriate instruction suffix (rebuild: LLMRequest is frozen).
        if state.pending_actions:
            instruction_suffix = (
                " You have not yet gathered enough evidence to answer the request. "
                "Call exactly one tool to gather more evidence. "
                "Do not produce a final response yet."
            )
        else:
            instruction_suffix = (
                " You have gathered evidence for all planned actions. "
                "If you have enough verified evidence to answer the request, "
                "produce a final_response with your answer. "
                "Otherwise call one more tool to gather missing evidence."
            )
        base_instruction = request_obj.system_instruction or ""
        request_obj = LLMRequest(
            user_request=request_obj.user_request,
            intent=request_obj.intent,
            tool_definitions=request_obj.tool_definitions,
            observations=request_obj.observations,
            verification=request_obj.verification,
            conversation=request_obj.conversation,
            system_instruction=(base_instruction + instruction_suffix),
            state_summary=dict(request_obj.state_summary),
            extra=dict(request_obj.extra),
        )

        state.record(
            TrajectoryStage.LLM_DECISION,
            f"llm_decision: step {state.llm_steps_used + 1} of {config.max_model_steps}",
        )

        # Inner retry loop: invalid proposals (malformed output or failed
        # tool-call validation) consume additional model calls within the
        # same step until retry_invalid is exceeded. valid_response is None
        # when the step must terminate; otherwise it holds the validated
        # model response to handle below.
        # NOTE: FakeLLMClient raises MalformedModelResponseError directly
        # for non-ModelResponse script entries (it never returns them), so
        # malformed output surfaces as an LLMError subclass from complete().
        valid_response = None
        while True:
            # Call the model.
            try:
                candidate = llm_client.complete(request_obj)
            except (MalformedModelResponseError, InvalidModelResponseError) as exc:
                # Malformed output raised by the client itself: retryable as
                # an invalid proposal (same budget as validation failures).
                consecutive_invalid += 1
                last_invalid_reason = str(exc)
                state.record(
                    TrajectoryStage.ERROR,
                    f"invalid model output (consecutive {consecutive_invalid}): {exc}",
                )
                state.errors.append(f"invalid model output: {exc}")
                if consecutive_invalid > config.retry_invalid:
                    state.termination_reason = LLMTerminationReason.MAX_RETRIES_INVALID.value
                    state.response_status = ResponseStatus.ERROR
                    state.response = (
                        "I'm having trouble processing your request right now. "
                        "Please try again or rephrase your question."
                    )
                    return state
                request_obj = _with_retry_instruction(request_obj)
                state.record(
                    TrajectoryStage.LLM_DECISION,
                    f"llm_decision retry ({consecutive_invalid} of {config.retry_invalid + 1}): invalid output, retrying",
                )
                continue
            except LLMError as exc:
                # Genuine model errors (timeout/unavailable/exhausted) are
                # terminal, EXCEPT ResponseSequenceExhaustedError raised by
                # FakeLLMClient: when the script is consumed but invalid
                # retries remain, treat exhaustion as "no recovery proposed"
                # and terminate as max_retries_invalid.
                from ..llm.errors import ResponseSequenceExhaustedError

                if isinstance(exc, ResponseSequenceExhaustedError) and (
                    consecutive_invalid > 0
                    or last_invalid_reason
                ):
                    state.termination_reason = (
                        LLMTerminationReason.MAX_RETRIES_INVALID.value
                    )
                    state.response_status = ResponseStatus.ERROR
                    state.record(
                        TrajectoryStage.ERROR,
                        f"model sequence exhausted during invalid retry: {exc}",
                    )
                    state.response = (
                        "I'm having trouble processing your request right now. "
                        "Please try again or rephrase your question."
                    )
                    return state
                state.termination_reason = LLMTerminationReason.MODEL_ERROR.value
                state.response_status = ResponseStatus.ERROR
                state.record(
                    TrajectoryStage.ERROR,
                    f"model error: {type(exc).__name__}: {exc}",
                )
                state.errors.append(f"model error: {exc}")
                state.response = _deterministic_response_from_state(state)
                return state

            # Validate the model's structured output.
            try:
                validate_model_response(candidate)
                tool_validation = None
                if candidate.response_type == RESPONSE_TYPE_TOOL_CALL:
                    tool_validation = validate_llm_tool_call(candidate.tool_call)
                    if not tool_validation.passed:
                        raise _InvalidProposalError(
                            f"tool call validation failed at layer "
                            f"'{tool_validation.layer}': {tool_validation.reason}"
                        )
            except (MalformedModelResponseError, InvalidModelResponseError,
                    _InvalidProposalError) as exc:
                consecutive_invalid += 1
                last_invalid_reason = str(exc)
                state.record(
                    TrajectoryStage.ERROR,
                    f"invalid model output (consecutive {consecutive_invalid}): {exc}",
                )
                state.errors.append(f"invalid model output: {exc}")

                if consecutive_invalid > config.retry_invalid:
                    state.termination_reason = LLMTerminationReason.MAX_RETRIES_INVALID.value
                    state.response_status = ResponseStatus.ERROR
                    state.response = (
                        "I'm having trouble processing your request right now. "
                        "Please try again or rephrase your question."
                    )
                    return state

                # Retry within the same step: rebuild the request with a
                # retry instruction appended (LLMRequest is frozen).
                request_obj = _with_retry_instruction(request_obj)
                state.record(
                    TrajectoryStage.LLM_DECISION,
                    f"llm_decision retry ({consecutive_invalid} of {config.retry_invalid + 1}): invalid output, retrying",
                )
                continue

            # Valid proposal for this step.
            valid_response = candidate
            break

        # Reset invalid counter on valid output.
        consecutive_invalid = 0
        last_invalid_reason = ""
        response = valid_response

        # Handle the response.
        if response.response_type == RESPONSE_TYPE_TOOL_CALL:
            # Already validated in the inner retry loop; re-validate
            # defensively (should always pass here).
            # --- Execute the validated tool call -----------------------------
            tool_name = response.tool_call.name.strip()
            tool_args = dict(response.tool_call.arguments)

            # Coerce LLM-provided period arguments into Period objects before
            # execution. The MVP tool contract accepts YYYY-MM strings (and
            # (year, month) pairs) from the model; execute_tool requires
            # Period instances. Coercion failures here are defensive: the
            # semantic layer should already have rejected them.
            try:
                tool_args = _coerce_tool_args_for_execution(tool_name, tool_args)
            except _CoercionError as exc:
                consecutive_invalid += 1
                last_invalid_reason = f"tool call coercion failed: {exc}"
                state.record(
                    TrajectoryStage.ERROR,
                    f"invalid tool call (consecutive {consecutive_invalid}): {last_invalid_reason}",
                )
                state.errors.append(last_invalid_reason)
                if consecutive_invalid > config.retry_invalid:
                    state.termination_reason = LLMTerminationReason.MAX_RETRIES_INVALID.value
                    state.response_status = ResponseStatus.ERROR
                    state.response = (
                        "I'm having trouble processing your request right now. "
                        "Please try again or rephrase your question."
                    )
                    return state
                continue

            # Detect repeated tool calls (same tool AND same coerced args).
            repeat_key = (tool_name, _repeat_key(tool_args))
            if repeat_key in repeated_calls:
                repeated_calls[repeat_key] += 1
            else:
                repeated_calls[repeat_key] = 1
                # A different argument set resets the identical-repeat counter
                # for this tool: only identical consecutive repeats are bounded.
                for key in [k for k in repeated_calls if k[0] == tool_name and k != repeat_key]:
                    del repeated_calls[key]

            if (
                repeated_calls[repeat_key]
                > config.max_consecutive_repeats
            ):
                state.termination_reason = LLMTerminationReason.MAX_CONSECUTIVE_REPEATS.value
                state.response_status = ResponseStatus.INCOMPLETE
                state.record(
                    TrajectoryStage.ERROR,
                    f"repeated tool call '{tool_name}' {repeated_calls[repeat_key]} times",
                )
                state.errors.append(
                    f"repeated tool call '{tool_name}' "
                    f"{repeated_calls[repeat_key]} times consecutively"
                )
                state.response = _deterministic_response_from_state(state)
                return state

            # Add transactions to params if missing.
            if "transactions" not in tool_args:
                tool_args["transactions"] = transactions

            state.record(
                TrajectoryStage.EXECUTE,
                f"execute tool '{tool_name}' with args {tool_args}",
            )
            try:
                result = execute_tool(tool_name, tool_args)
            except (ToolError, ValueError) as exc:
                state.record(
                    TrajectoryStage.ERROR,
                    f"tool '{tool_name}' failed: {exc}",
                )
                state.observations.append(
                    Observation(
                        action_name=tool_name,
                        success=False,
                        error=str(exc),
                    )
                )
                state.errors.append(f"{tool_name}: {exc}")
                # Still record observation summary for model context.
                observation_summaries.append(
                    summarise_observation_for_llm(
                        state.observations[-1]
                    )
                )
                continue

            # Record observation.
            state.record(
                TrajectoryStage.OBSERVE,
                f"record observation for '{tool_name}'",
            )
            state.observations.append(
                Observation(
                    action_name=tool_name,
                    success=True,
                    result=result,
                )
            )
            state.completed_actions.append(tool_name)
            state.tool_calls_used += 1
            state.llm_steps_used += 1

            # Verification.
            state.record(
                TrajectoryStage.VERIFY,
                f"verify result of '{tool_name}'",
            )
            trust, verification_detail = verify_for(
                tool_name, result, transactions
            )
            state.verification_records.append(
                VerificationRecord(
                    action_name=tool_name,
                    status=(
                        verification_detail.status
                        if verification_detail is not None
                        else "unverified"
                    ),
                    trust=trust,
                    detail=verification_detail,
                )
            )

            # Update summaries for next request.
            observation_summaries.append(
                summarise_observation_for_llm(state.observations[-1])
            )
            verification_summaries.append(_summarise_verification(state.verification_records[-1]))

            # Consume the matching planned pending action (if any) so the
            # runtime does not re-execute evidence the model just gathered.
            # Matching is by tool name only (MVP): the plan carries Period
            # objects while the model proposes YYYY-MM strings, so argument
            # equality would never match. Consuming by name prevents duplicate
            # execution of the same planned evidence while keeping validation,
            # execution, and verification of the model's own proposal intact.
            _consume_matching_pending_action(state, tool_name)

            # Replanning: if no pending actions remain, let the model decide
            # whether to call another tool or produce a final response.
            if not state.pending_actions:
                continue

            # Deterministic gap-fill for remaining planned evidence the model
            # has not yet proposed (hybrid behavior, DEC-023). The pending
            # action goes through the same execute -> observe -> verify path
            # as a model proposal (no validation bypass: the plan is
            # deterministic, not model input), and its budget consumption is
            # enforced before execution. If the tool budget is exhausted the
            # loop terminates instead of executing.
            if state.tool_calls_used >= config.max_tool_calls:
                state.termination_reason = LLMTerminationReason.BUDGET_TOOL_CALLS.value
                state.response_status = ResponseStatus.INCOMPLETE
                state.record(
                    TrajectoryStage.ERROR,
                    f"tool call budget exhausted ({config.max_tool_calls})",
                )
                state.response = _deterministic_response_from_state(state)
                return state
            if state.llm_steps_used >= config.max_model_steps:
                state.termination_reason = LLMTerminationReason.BUDGET_STEPS.value
                state.response_status = ResponseStatus.INCOMPLETE
                state.record(
                    TrajectoryStage.ERROR,
                    f"model step budget exhausted ({config.max_model_steps})",
                )
                state.response = _deterministic_response_from_state(state)
                return state
            action = state.pending_actions.pop(0)
            state.record(
                TrajectoryStage.EXECUTE,
                f"execute pending action '{action.name}'",
            )
            params = dict(action.params)
            if "transactions" not in params:
                params["transactions"] = transactions
            try:
                result = execute_tool(action.name, params)
            except (ToolError, ValueError) as exc:
                state.record(
                    TrajectoryStage.ERROR,
                    f"pending action '{action.name}' failed: {exc}",
                )
                state.observations.append(
                    Observation(
                        action_name=action.name,
                        success=False,
                        error=str(exc),
                    )
                )
                state.errors.append(f"{action.name}: {exc}")
                observation_summaries.append(
                    summarise_observation_for_llm(state.observations[-1])
                )
                continue

            state.record(
                TrajectoryStage.OBSERVE,
                f"record observation for '{action.name}'",
            )
            state.observations.append(
                Observation(
                    action_name=action.name,
                    success=True,
                    result=result,
                )
            )
            state.completed_actions.append(action.name)
            state.tool_calls_used += 1

            state.record(
                TrajectoryStage.VERIFY,
                f"verify result of '{action.name}'",
            )
            trust, verification_detail = verify_for(
                action.name, result, transactions
            )
            state.verification_records.append(
                VerificationRecord(
                    action_name=action.name,
                    status=(
                        verification_detail.status
                        if verification_detail is not None
                        else "unverified"
                    ),
                    trust=trust,
                    detail=verification_detail,
                )
            )

            observation_summaries.append(
                summarise_observation_for_llm(state.observations[-1])
            )
            verification_summaries.append(
                _summarise_verification(state.verification_records[-1])
            )

        elif response.response_type == RESPONSE_TYPE_FINAL:
            # The model produced a final response draft.
            state.llm_steps_used += 1
            draft = response.content
            if not isinstance(draft, str) or not draft.strip():
                consecutive_invalid += 1
                last_invalid_reason = "final response content is empty"
                state.record(
                    TrajectoryStage.ERROR,
                    f"invalid final response (consecutive {consecutive_invalid}): empty content",
                )
                state.errors.append(last_invalid_reason)
                if consecutive_invalid > config.retry_invalid:
                    state.termination_reason = LLMTerminationReason.MAX_RETRIES_INVALID.value
                    state.response_status = ResponseStatus.ERROR
                    state.response = (
                        "I'm having trouble processing your request right now. "
                        "Please try again or rephrase your question."
                    )
                    return state
                request_obj = _with_retry_instruction(request_obj)
                continue

            # Grounding gate.
            gate_result = grounding_gate(draft, state)
            if not gate_result.passed:
                state.termination_reason = LLMTerminationReason.GROUNDING_FALLBACK.value
                state.response_status = ResponseStatus.INCOMPLETE
                state.record(
                    TrajectoryStage.ERROR,
                    f"grounding gate failed: {gate_result.note}",
                )
                state.errors.append(f"grounding gate failed: {gate_result.note}")
                state.response = _deterministic_response_from_state(state)
                return state

            # Grounding passed: use the draft as the response.
            state.response = draft
            state.response_status = ResponseStatus.VERIFIED
            state.termination_reason = LLMTerminationReason.RESPONSE_COMPLETE.value
            state.record(
                TrajectoryStage.RESPOND,
                "respond: final response from model (grounded)",
            )
            return state

        else:
            # Defensive: should not happen after validate_model_response.
            consecutive_invalid += 1
            last_invalid_reason = f"unexpected response type: {response.response_type}"
            if consecutive_invalid > config.retry_invalid:
                state.termination_reason = LLMTerminationReason.MAX_RETRIES_INVALID.value
                state.response_status = ResponseStatus.ERROR
                state.response = (
                    "I'm having trouble processing your request right now. "
                    "Please try again or rephrase your question."
                )
                return state
            continue

    # Unreachable: loop always returns.
    return state



# ---------------------------------------------------------------------------
# Implementation notes
# ---------------------------------------------------------------------------
#
# * DEFAULT_TOOL_DEFINITIONS is imported at the top of the module (line 48)
#   from ..llm.tool_definitions. The earlier note about importing it here to
#   avoid circular imports is stale and has been removed.
# ---------------------------------------------------------------------------
