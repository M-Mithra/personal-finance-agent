"""Typed lifecycle vocabulary and the explicit agent state.

The runtime state is a single inspectable value that records every stage of the
agent lifecycle (docs/04_agent_design.md sections 6-12): the original request,
the interpreted intent, the plan, every executed action, every observation, every
verification result, errors, assumptions, the execution trajectory, and the final
response.

The state is intentionally verbose. It is the primary artifact a future evaluator
inspects to determine not only whether the final answer was correct, but whether
the agent took the correct actions to reach it.

No global mutable state: each AgentState is constructed fresh for a
request and mutated only through the runtime loop in agent.py.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "Action",
    "AgentState",
    "Intent",
    "IntentStatus",
    "Observation",
    "ResponseStatus",
    "TrajectoryEntry",
    "TrajectoryStage",
    "VerificationRecord",
]


class Intent(StrEnum):
    """Supported intents recognized by the deterministic understanding layer."""

    SPENDING_SUMMARY = "spending_summary"
    CATEGORY_ANALYSIS = "category_analysis"
    PERIOD_COMPARISON = "period_comparison"
    MERCHANT_ANALYSIS = "merchant_analysis"
    NOTEWORTHY_TRANSACTIONS = "noteworthy_transactions"
    SPENDING_CHANGE_EXPLANATION = "spending_change_explanation"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"


class IntentStatus(StrEnum):
    """Whether the understanding layer produced a usable intent."""

    RECOGNIZED = "recognized"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"


class ResponseStatus(StrEnum):
    """Final outcome of the agent runtime for a request."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED_VERIFICATION = "failed_verification"
    INCOMPLETE = "incomplete"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"
    ERROR = "error"


class TrajectoryStage(StrEnum):
    """Lifecycle stages recorded in the execution trajectory."""

    RECEIVED = "received"
    UNDERSTAND = "understand"
    PLAN = "plan"
    EXECUTE = "execute"
    OBSERVE = "observe"
    VERIFY = "verify"
    REPLAN = "replan"
    RESPOND = "respond"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Action:
    """One planned analytical action."""

    name: str
    params: dict[str, object] = field(default_factory=dict)
    purpose: str = ""


@dataclass(frozen=True, slots=True)
class Observation:
    """Structured record of one executed action."""

    action_name: str
    success: bool
    result: object | None = None
    error: str | None = None
    verification: object | None = None


@dataclass(frozen=True, slots=True)
class VerificationRecord:
    """A verification outcome paired with the action that produced it."""

    action_name: str
    status: str
    trust: str
    detail: object | None = None


@dataclass(frozen=True, slots=True)
class TrajectoryEntry:
    """One step in the execution trajectory."""

    stage: TrajectoryStage
    description: str
    recorded_at: str = field(
        default_factory=lambda: _dt.datetime.now(_dt.timezone.utc).isoformat()
    )


@dataclass(slots=True)
class AgentState:
    """Explicit, inspectable state for one agent request."""

    request: str
    intent: Intent = Intent.UNSUPPORTED
    intent_status: IntentStatus = IntentStatus.UNSUPPORTED
    intent_detail: str = ""
    periods: list[object] = field(default_factory=list)
    plan: list[Action] = field(default_factory=list)
    pending_actions: list[Action] = field(default_factory=list)
    completed_actions: list[str] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    verification_records: list[VerificationRecord] = field(default_factory=list)
    model_identifier: str | None = None
    errors: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    trajectory: list[TrajectoryEntry] = field(default_factory=list)
    response_status: ResponseStatus = ResponseStatus.PENDING
    response: str = ""
    response_evidence: list[str] = field(default_factory=list)

    def record(self, stage: TrajectoryStage, description: str) -> None:
        """Append a trajectory entry."""
        self.trajectory.append(
            TrajectoryEntry(stage=stage, description=description)
        )

    def observation_for(self, action_name: str) -> Observation | None:
        """Return the most recent observation for an action name."""
        for observation in reversed(self.observations):
            if observation.action_name == action_name:
                return observation
        return None

    def verified(self, action_name: str) -> bool:
        """True when the action result was verified and trusted."""
        for record in self.verification_records:
            if record.action_name == action_name and record.trust == "verified":
                return True
        return False
