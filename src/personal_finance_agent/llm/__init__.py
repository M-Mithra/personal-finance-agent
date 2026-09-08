"""Provider-neutral LLM abstraction.

This package (``docs/10_llm_integration_design.md`` sections 16) defines the
boundary between the Agent Runtime and any future model:

* ``types``            : provider-neutral structures exchanged with a model
  (``ToolCall``, ``ModelResponse``, ``LLMRequest``).
* ``errors``           : provider-neutral error vocabulary for model failures.
* ``tool_definitions`` : metadata describing the available analytical tools to
  a model (name, description, argument contract).
* ``client``           : the ``LLMClient`` abstraction plus an independent
  ``validate_model_response`` checker.
* ``fake``             : a deterministic scripted ``FakeLLMClient`` for tests.

This package contains **no provider SDK, no credentials, and no automatic model
context**: it only defines types and interfaces. The Agent Runtime keeps the
responsibility for validating, executing, verifying, and terminating.
"""

from __future__ import annotations

from .client import LLMClient, validate_model_response
from .errors import (
    ContextLengthError,
    InvalidModelResponseError,
    LLMError,
    MalformedModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
    ResponseSequenceExhaustedError,
)
from .fake import FakeLLMClient
from .tool_definitions import (
    DEFAULT_TOOL_DEFINITIONS,
    ToolArgumentSchema,
    ToolDefinition,
    tool_definition_for,
)
from .types import (
    RESPONSE_TYPE_FINAL,
    RESPONSE_TYPE_TOOL_CALL,
    VALID_RESPONSE_TYPES,
    ConversationTurn,
    LLMRequest,
    ModelMetadata,
    ModelResponse,
    ToolCall,
)

__all__ = [
    "ContextLengthError",
    "ConversationTurn",
    "DEFAULT_TOOL_DEFINITIONS",
    "FakeLLMClient",
    "InvalidModelResponseError",
    "LLMClient",
    "LLMError",
    "LLMRequest",
    "MalformedModelResponseError",
    "ModelMetadata",
    "ModelResponse",
    "ModelTimeoutError",
    "ModelUnavailableError",
    "RESPONSE_TYPE_FINAL",
    "RESPONSE_TYPE_TOOL_CALL",
    "ResponseSequenceExhaustedError",
    "ToolArgumentSchema",
    "ToolCall",
    "ToolDefinition",
    "VALID_RESPONSE_TYPES",
    "tool_definition_for",
    "validate_model_response",
]