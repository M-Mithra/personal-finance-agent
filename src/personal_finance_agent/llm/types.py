"""Provider-neutral structures for LLM interactions.

This module defines the types exchanged between the Agent Runtime and any LLM
client. They intentionally contain **no provider-specific request or response
types**: a provider-backed client adapts its SDK at the boundary and everything
else in the system only sees these structures.

Two response kinds are supported (``docs/10_llm_integration_design.md``
section 7):

* a tool/action request that the runtime must validate before executing;
* a final response containing natural-language content.

Model metadata (identifier, optional usage counts) is carried when useful for
observability but never assumed to be present. Free-form reasoning traces and
chain-of-thought are deliberately not stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .tool_definitions import ToolDefinition

__all__ = [
    "ConversationTurn",
    "LLMRequest",
    "ModelMetadata",
    "ModelResponse",
    "RESPONSE_TYPE_FINAL",
    "RESPONSE_TYPE_TOOL_CALL",
    "VALID_RESPONSE_TYPES",
    "ToolCall",
]

RESPONSE_TYPE_TOOL_CALL = "tool_call"
RESPONSE_TYPE_FINAL = "final_response"
VALID_RESPONSE_TYPES = frozenset({RESPONSE_TYPE_TOOL_CALL, RESPONSE_TYPE_FINAL})


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A model-proposed tool/action invocation.

    ``arguments`` must remain a structured mapping; tool calls are never
    represented as free-form natural-language text. Constructing a
    ``ToolCall`` does not execute anything: execution is the runtime's
    responsibility after validation.
    """

    name: str
    arguments: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    """Optional metadata attached to a model response for observability."""

    model_identifier: str
    provider: str | None = None
    usage: dict[str, object] = field(default_factory=dict)
    extra: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelResponse:
    """Provider-neutral structured model output.

    Exactly one outcome is meaningful per response: either a tool call
    request (``response_type == RESPONSE_TYPE_TOOL_CALL``) or a final
    response (``response_type == RESPONSE_TYPE_FINAL``). Use the
    ``tool_call_request`` and ``final_response`` constructors to build
    well-formed responses.
    """

    response_type: str
    tool_call: ToolCall | None = None
    content: str | None = None
    metadata: ModelMetadata | None = None

    @classmethod
    def tool_call_request(
        cls,
        name: str,
        arguments: dict[str, object] | None = None,
        metadata: ModelMetadata | None = None,
    ) -> "ModelResponse":
        """Build a well-formed tool/action request response."""
        return cls(
            response_type=RESPONSE_TYPE_TOOL_CALL,
            tool_call=ToolCall(name=name, arguments=dict(arguments or {})),
            metadata=metadata,
        )

    @classmethod
    def final_response(
        cls,
        content: str,
        metadata: ModelMetadata | None = None,
    ) -> "ModelResponse":
        """Build a well-formed final response."""
        return cls(
            response_type=RESPONSE_TYPE_FINAL,
            content=content,
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """One prior exchange supplied as conversation context."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """Provider-neutral structured context sent to the LLM.

    The request carries the information the model needs for one reasoning
    step: the user request, the interpreted intent, tool definitions,
    structured observations, verification information, relevant conversation,
    and system/instruction content. Raw transactions are **not** a field here:
    transactions reach the model only as aggregated, verified analytical
    results supplied through ``observations``.
    """

    user_request: str
    intent: str | None = None
    tool_definitions: tuple[ToolDefinition, ...] = ()
    observations: tuple[object, ...] = ()
    verification: tuple[object, ...] = ()
    conversation: tuple[ConversationTurn, ...] = ()
    system_instruction: str | None = None
    state_summary: dict[str, object] = field(default_factory=dict)
    extra: dict[str, object] = field(default_factory=dict)