"""The deterministic agent runtime loop.

Wires the lifecycle stages into a single executable function
(:func:`run`): receive request, understand, plan, execute, observe, verify,
replan, and respond. Every stage records a trajectory entry and updates the
explicit :class:`AgentState`, which is returned fully populated so the entire
execution can be inspected.

By default the runtime uses only the deterministic modules in this package plus
the analytical foundation. An optional provider-neutral ``llm_client`` may be
injected (see ``docs/10_llm_integration_design.md``); in this phase the
injectable client is only recorded for observability and does not alter the
deterministic lifecycle, which remains the baseline until the first
model-powered slice is implemented. No LLM framework or external service is
required.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..models import Transaction
from .checks import TRUST_FAILED, TRUST_INCONCLUSIVE, classify_trust, verify_for
from .planning import plan_for
from .replanning import decide_followups
from .response import generate_response
from .state import (
    Action,
    AgentState,
    Intent,
    IntentStatus,
    Observation,
    ResponseStatus,
    TrajectoryStage,
    VerificationRecord,
)
from .tools import ToolError, execute_tool
from .understanding import understand

if TYPE_CHECKING:
    from ..llm.client import LLMClient

__all__ = ["run", "Agent"]


def _verify_and_record(
    state: AgentState, action_name: str, result: object, transactions: Sequence[Transaction]
) -> None:
    """Run verification for a tool result and record the outcome."""
    trust, detail = verify_for(action_name, result, transactions)
    state.verification_records.append(
        VerificationRecord(
            action_name=action_name,
            status=detail.status if detail else "unverified",
            trust=trust,
            detail=detail,
        )
    )


def _execute_action(
    state: AgentState, action: Action, transactions: Sequence[Transaction]
) -> None:
    """Execute one action, record its observation and verification."""
    params = dict(action.params)
    if "transactions" not in params:
        params["transactions"] = transactions

    state.record(TrajectoryStage.EXECUTE, f"execute tool '{action.name}'")
    try:
        result = execute_tool(action.name, params)
    except (ToolError, ValueError) as exc:
        state.record(TrajectoryStage.ERROR, f"tool '{action.name}' failed: {exc}")
        state.observations.append(
            Observation(
                action_name=action.name,
                success=False,
                error=str(exc),
            )
        )
        state.errors.append(f"{action.name}: {exc}")
        return

    state.record(TrajectoryStage.OBSERVE, f"record observation for '{action.name}'")
    state.observations.append(
        Observation(action_name=action.name, success=True, result=result)
    )
    state.completed_actions.append(action.name)

    state.record(TrajectoryStage.VERIFY, f"verify result of '{action.name}'")
    _verify_and_record(state, action.name, result, transactions)
def run(
    request: str,
    transactions: Sequence[Transaction],
    llm_client: "LLMClient | None" = None,
) -> AgentState:
    """Execute the full deterministic agent lifecycle for a request.

    Returns a fully populated :class:`AgentState` whose ``trajectory`` records
    every lifecycle stage and whose ``response`` holds the grounded natural
    language answer. The state is inspectable after execution.

    ``llm_client`` is the provider-neutral injection point defined in
    ``docs/10_llm_integration_design.md``. When provided, its model identity is
    recorded on the state for observability; the deterministic lifecycle is
    otherwise unchanged and makes no model calls in this phase.
    """
    state = AgentState(request=request)
    if llm_client is not None:
        identifier = getattr(llm_client, "model_identifier", None)
        state.model_identifier = identifier or type(llm_client).__name__
        state.record(
            TrajectoryStage.RECEIVED,
            f"LLM client injected: {state.model_identifier}",
        )
    state.record(TrajectoryStage.RECEIVED, f"received request: {request!r}")

    # 1. Understand.
    state.record(TrajectoryStage.UNDERSTAND, "understand request")
    understanding = understand(request)
    state.intent = understanding.intent
    state.intent_status = understanding.intent_status
    state.intent_detail = understanding.detail
    state.periods = list(understanding.periods)
    state.assumptions.extend(understanding.warnings)

    if understanding.intent_status is IntentStatus.UNSUPPORTED:
        state.response_status = ResponseStatus.UNSUPPORTED
        state.record(TrajectoryStage.RESPOND, "respond: unsupported request")
        state.response = generate_response(state)
        return state

    if understanding.intent_status is IntentStatus.AMBIGUOUS:
        state.response_status = ResponseStatus.AMBIGUOUS
        state.record(TrajectoryStage.RESPOND, "respond: ambiguous request")
        state.response = generate_response(state)
        return state

    # 2. Plan.
    state.record(TrajectoryStage.PLAN, "plan actions")
    state.plan = list(plan_for(understanding))
    state.pending_actions = list(state.plan)

    if not state.plan:
        state.response_status = ResponseStatus.INCOMPLETE
        state.errors.append("planner produced no actions for a recognized intent")
        state.record(TrajectoryStage.RESPOND, "respond: empty plan")
        state.response = generate_response(state)
        return state

    # 3. Execute, observe, verify — with bounded replanning.
    while state.pending_actions:
        action = state.pending_actions.pop(0)
        _execute_action(state, action, transactions)

        # 4. Replanning: inspect results and add follow-up actions.
        state.record(TrajectoryStage.REPLAN, "consider follow-up actions")
        followups = decide_followups(state)
        if followups:
            for followup in followups:
                if followup not in state.pending_actions:
                    state.pending_actions.append(followup)
                    state.assumptions.append(
                        f"follow-up action added: {followup.name}"
                    )

    # 5. Final verification assessment.
    failed = [
        record
        for record in state.verification_records
        if record.trust == TRUST_FAILED
    ]
    if failed:
        state.response_status = ResponseStatus.FAILED_VERIFICATION
        state.errors.append(
            f"{len(failed)} verification(s) failed: "
            + ", ".join(record.action_name for record in failed)
        )
    else:
        state.response_status = ResponseStatus.VERIFIED

    # 6. Respond.
    state.record(TrajectoryStage.RESPOND, "generate response")
    state.response = generate_response(state)
    return state


class Agent:
    """Thin stateful wrapper around :func:`run`.

    Holds the loaded transaction set so repeated requests can be executed
    against the same data without reloading. The agent itself is stateless
    across requests except for the transaction set it carries.

    An optional provider-neutral ``llm_client`` may be injected for future
    model-powered interactions. In this phase it is carried (and its identity
    recorded per execution) without affecting the deterministic lifecycle.
    """

    def __init__(
        self,
        transactions: Sequence[Transaction],
        llm_client: "LLMClient | None" = None,
    ) -> None:
        self.transactions = tuple(transactions)
        self.llm_client = llm_client

    @property
    def has_llm_client(self) -> bool:
        """True when a client has been injected."""
        return self.llm_client is not None

    def execute(self, request: str) -> AgentState:
        """Run the agent lifecycle against the carried transactions."""
        return run(request, self.transactions, llm_client=self.llm_client)
