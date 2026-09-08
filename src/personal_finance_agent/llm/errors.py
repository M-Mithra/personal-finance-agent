"""Provider-neutral errors for LLM client interactions.

These errors are the vocabulary the Agent Runtime uses when an LLM interaction
fails. They deliberately make **no provider-specific assumptions**: a real
provider-backed client maps its own SDK exceptions onto these types, and the
runtime only ever handles these types.

No retry policy is defined here; retry limits and provider-specific error
mapping remain TBD (``docs/10_llm_integration_design.md`` section 26).
"""

from __future__ import annotations

__all__ = [
    "ContextLengthError",
    "InvalidModelResponseError",
    "LLMError",
    "MalformedModelResponseError",
    "ModelTimeoutError",
    "ModelUnavailableError",
    "ResponseSequenceExhaustedError",
]


class LLMError(Exception):
    """Base class for all LLM client failures.

    This is the single error type the runtime needs to catch to apply the
    fail-safe policy. Subclasses add classification while remaining catchable
    through this base.
    """


class MalformedModelResponseError(LLMError):
    """The model output could not be parsed into a structured response."""


class InvalidModelResponseError(LLMError):
    """The model output parsed but failed structural validation.

    Examples: an unknown response type, a tool call without a structured
    arguments mapping, or a final response without content.
    """


class ModelUnavailableError(LLMError):
    """The model or provider could not be reached or returned a service error."""


class ModelTimeoutError(LLMError):
    """The model did not respond within the timeout budget."""


class ContextLengthError(LLMError):
    """The constructed context exceeded the model's context window."""


class ResponseSequenceExhaustedError(LLMError):
    """A scripted client has no more responses to return.

    Primarily raised by the deterministic ``FakeLLMClient`` when its configured
    response sequence is consumed, so the runtime can test defensive behavior
    against a model that stops producing output.
    """