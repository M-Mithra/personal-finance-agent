"""Provider-neutral LLM client interface.

``LLMClient`` is the boundary the Agent Runtime will use to interact with any
model (``docs/10_llm_integration_design.md`` section 16). It is deliberately
free of provider SDKs: a real provider-backed client adapts its SDK to this
interface, and the rest of the system only depends on this abstraction.

The interface supports two interaction kinds:

* ``reason`` — a reasoning/request interaction that may result in a
  tool/action request or a final response;
* ``generate_response`` — final response generation.

Both interact with the model through the single ``complete`` hook so a client
only needs to implement one method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .errors import (
    InvalidModelResponseError,
    MalformedModelResponseError,
)
from .types import (
    RESPONSE_TYPE_FINAL,
    RESPONSE_TYPE_TOOL_CALL,
    VALID_RESPONSE_TYPES,
    LLMRequest,
    ModelResponse,
)

__all__ = [
    "LLMClient",
    "validate_model_response",
]


class LLMClient(ABC):
    """Abstract provider-neutral interface to a language model.

    Implementations must provide a stable :attr:`model_identifier` and the
    ``complete`` method. The default ``reason`` and ``generate_response``
    methods dispatch to ``complete``; each subclass may override them if a
    provider interaction genuinely differs by interaction kind.
    """

    @property
    @abstractmethod
    def model_identifier(self) -> str:
        """Stable identifier for the model/backing implementation."""

    @abstractmethod
    def complete(self, request: LLMRequest) -> ModelResponse:
        """Send one structured request and return a structured response.

        Must raise a subclass of
        :class:`~personal_finance_agent.llm.errors.LLMError` on failure
        (malformed output, unavailability, timeout, context overflow, ...).
        Must not execute tools, access transactions, or mutate state: it only
        returns the model's proposed action or final response.
        """

    def reason(self, request: LLMRequest) -> ModelResponse:
        """Reasoning/request interaction (may propose a tool call)."""
        return self.complete(request)

    def generate_response(self, request: LLMRequest) -> ModelResponse:
        """Final response generation interaction."""
        return self.complete(request)


def validate_model_response(response: object) -> None:
    """Independently validate a structured model response.

    Raises :class:`MalformedModelResponseError` when ``response`` is not a
    :class:`ModelResponse`, and :class:`InvalidModelResponseError` when its
    structure is inconsistent (unknown response type, tool call missing a
    structured name/arguments, final response missing content, or a response
    mixing both kinds).

    This is a pure function the runtime can rely on regardless of which client
    produced the response. It performs no execution and makes no assumptions
    about any provider.
    """
    if not isinstance(response, ModelResponse):
        raise MalformedModelResponseError(
            f"model output is not a structured ModelResponse: "
            f"{type(response).__name__}"
        )

    if response.response_type not in VALID_RESPONSE_TYPES:
        raise InvalidModelResponseError(
            f"invalid model response type: {response.response_type!r}; "
            f"expected one of {sorted(VALID_RESPONSE_TYPES)}"
        )

    if response.response_type == RESPONSE_TYPE_TOOL_CALL:
        if response.tool_call is None:
            raise InvalidModelResponseError(
                "tool_call response is missing its ToolCall"
            )
        if not isinstance(response.tool_call.name, str) or not response.tool_call.name.strip():
            raise InvalidModelResponseError(
                "tool call name must be a non-empty string"
            )
        if not isinstance(response.tool_call.arguments, dict):
            raise InvalidModelResponseError(
                "tool call arguments must be a structured mapping, "
                "not free-form text"
            )
        if response.content is not None:
            raise InvalidModelResponseError(
                "a tool_call response must not carry free-form content"
            )
        return

    if response.response_type == RESPONSE_TYPE_FINAL:
        if not isinstance(response.content, str) or not response.content.strip():
            raise InvalidModelResponseError(
                "a final response must contain non-empty string content"
            )
        if response.tool_call is not None:
            raise InvalidModelResponseError(
                "a final response must not carry a tool call"
            )
        return

    raise InvalidModelResponseError(  # defensive; VALID_RESPONSE_TYPES guards above
        f"unknown response type: {response.response_type!r}"
    )