"""Deterministic fake LLM client for tests and local development.

``FakeLLMClient`` behaves like an unreliable external model so the Agent Runtime
can test defensive behavior deterministically:

* It returns a scripted sequence of structured responses in order.
* It records every request it receives for inspection.
* It can be scripted to raise model failures (unavailable, timeout, ...),
  emit malformed output, and exhaust its response sequence.

It never silently corrects invalid outputs: whatever the test scripts is
returned as-is, and malformed scripted entries raise
:class:`~personal_finance_agent.llm.errors.MalformedModelResponseError`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .client import LLMClient
from .errors import (
    MalformedModelResponseError,
    ResponseSequenceExhaustedError,
)
from .types import LLMRequest, ModelResponse

__all__ = ["FakeLLMClient"]

_FAKE_MODEL_IDENTIFIER = "fake-llm-client"


class FakeLLMClient(LLMClient):
    """A scriptable deterministic LLM client.

    Parameters
    ----------
    responses:
        An ordered sequence of items to return/raise on each call. Each item
        is one of:

        * a :class:`ModelResponse` (returned verbatim, never validated or
          corrected);
        * an ``Exception`` instance (raised, e.g. ``ModelUnavailableError``);
        * any other object (raises ``MalformedModelResponseError``, simulating
          output that cannot be parsed into a structured response).

        When the sequence is exhausted, subsequent calls raise
        :class:`ResponseSequenceExhaustedError`.
    """

    def __init__(
        self,
        responses: Sequence[Any] | None = None,
        *,
        model_identifier: str = _FAKE_MODEL_IDENTIFIER,
    ) -> None:
        self._responses: list[Any] = list(responses or [])
        self._index = 0
        self._model_identifier = model_identifier
        self.requests: list[LLMRequest] = []

    @property
    def model_identifier(self) -> str:
        return self._model_identifier

    @property
    def remaining(self) -> int:
        """Number of un-consumed scripted responses."""
        return max(0, len(self._responses) - self._index)

    def complete(self, request: LLMRequest) -> ModelResponse:
        """Return the next scripted response, recording the request first.

        The request is always recorded, including for failures, so tests can
        inspect exactly which context produced a failure.
        """
        self.requests.append(request)
        if self._index >= len(self._responses):
            raise ResponseSequenceExhaustedError(
                f"fake model exhausted its response sequence after "
                f"{self._index} call(s)"
            )
        item = self._responses[self._index]
        self._index += 1

        if isinstance(item, Exception):
            raise item
        if not isinstance(item, ModelResponse):
            raise MalformedModelResponseError(
                f"model output could not be parsed into a ModelResponse: "
                f"{type(item).__name__} ({item!r})"
            )
        return item

    # --- Convenience builders for configuring a response sequence -----------

    @staticmethod
    def tool_call(name: str, arguments: dict[str, object] | None = None) -> ModelResponse:
        """Build a scripted tool-call response."""
        return ModelResponse.tool_call_request(name=name, arguments=arguments)

    @staticmethod
    def final_response(content: str) -> ModelResponse:
        """Build a scripted final response."""
        return ModelResponse.final_response(content=content)