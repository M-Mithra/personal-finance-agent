"""Ollama-backed implementation of the provider-neutral LLMClient.

This adapter translates the provider-neutral ``LLMClient`` interface
(``llm/client.py``) into Ollama's local HTTP chat API. It is a thin
transport/protocol adapter only: it does not execute tools, compute financial
results, verify evidence, or mutate agent state.

The adapter uses Python's standard library only (``urllib``, ``json``,
``socket``). No Ollama SDK or third-party HTTP library is required.

Provider/transport failures are mapped onto the provider-neutral error
hierarchy defined in ``llm/errors.py``.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any

from .client import LLMClient, validate_model_response
from .errors import (
    ContextLengthError,
    InvalidModelResponseError,
    LLMError,
    MalformedModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from .tool_definitions import ToolDefinition
from .types import ConversationTurn, LLMRequest, ModelMetadata, ModelResponse

__all__ = ["OllamaLLMClient"]

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_TIMEOUT = 120.0
_CHAT_ENDPOINT = "/api/chat"

# Phrases that, in an Ollama HTTP 400 error body, indicate a context-length /
# token-limit problem rather than a generic bad request.
_CONTEXT_LENGTH_PHRASES = (
    "context length",
    "context_length",
    "token limit",
    "too long",
    "maximum context",
    "exceeds context",
    "context size",
    "prompt too long",
)


class OllamaLLMClient(LLMClient):
    """Ollama-backed :class:`LLMClient`.

    The adapter is a thin transport layer. It proposes nothing, executes
    nothing, and verifies nothing. The deterministic Agent Runtime remains the
    control boundary.

    Parameters
    ----------
    model:
        Ollama model name, e.g. ``"qwen3:1.7b"``.
    base_url:
        Ollama server base URL.
    timeout:
        Per-request timeout in seconds. Defaults to 120s to accommodate slow
        local inference on constrained hardware.
    system_instruction:
        Default system instruction used when the request does not supply one.
    request_format:
        Optional Ollama ``format`` value (e.g. ``"json"``). When ``None``, the
        ``format`` field is omitted from requests.
    options:
        Optional Ollama model options (e.g. ``temperature``), forwarded as the
        ``options`` field of the chat payload.
    """

    def __init__(
        self,
        *,
        model: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        system_instruction: str | None = None,
        request_format: str | None = None,
        options: dict[str, object] | None = None,
    ) -> None:
        if not model or not isinstance(model, str):
            raise ValueError("model must be a non-empty string")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = float(timeout)
        self._system_instruction = system_instruction
        self._request_format = request_format
        self._options = dict(options) if options else {}

    @property
    def model_identifier(self) -> str:
        """Stable identifier for observability, e.g. ``"ollama:qwen3:1.7b"``."""
        return f"ollama:{self._model}"

    def complete(self, request: LLMRequest) -> ModelResponse:
        """Send one structured request to Ollama and return a structured response.

        The response is validated with :func:`validate_model_response` before
        being returned, so a malformed provider response never reaches the
        runtime as a valid result.
        """
        payload = self._build_payload(request)

        try:
            data = self._post(f"{self._base_url}{_CHAT_ENDPOINT}", payload)
        except LLMError:
            raise
        except Exception as exc:
            raise ModelUnavailableError(
                f"unexpected error calling Ollama at {self._base_url}: {exc}"
            ) from exc

        response = self._parse_response(data)
        validate_model_response(response)
        return response

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a JSON payload to Ollama and return the decoded JSON body.

        Transport failures are mapped onto the provider-neutral error
        hierarchy. Only HTTP 400 responses whose error body clearly indicates
        a context/token-limit problem become :class:`ContextLengthError`;
        other HTTP errors become :class:`ModelUnavailableError`.
        """
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self._timeout) as http_response:
                raw = http_response.read().decode("utf-8")
        except (TimeoutError, socket.timeout) as exc:
            raise ModelTimeoutError(
                f"Ollama request to {url} timed out after {self._timeout}s"
            ) from exc
        except urllib.error.HTTPError as exc:
            detail = self._read_http_error(exc)
            if exc.code == 400 and _indicates_context_length(detail):
                raise ContextLengthError(
                    f"Ollama rejected the request as too long: {detail}"
                ) from exc
            raise ModelUnavailableError(
                f"Ollama returned HTTP {exc.code} for {url}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ModelUnavailableError(
                f"could not reach Ollama at {url}: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise ModelUnavailableError(
                f"could not reach Ollama at {url}: {exc}"
            ) from exc
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MalformedModelResponseError(
                f"Ollama returned invalid JSON: {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise MalformedModelResponseError(
                "Ollama response was not a JSON object"
            )
        return parsed

    @staticmethod
    def _read_http_error(exc: urllib.error.HTTPError) -> str:
        """Best-effort extraction of an HTTPError body without leaking secrets."""
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception:
            return f"HTTP {exc.code}"
        if len(raw) > 500:
            raw = raw[:500] + "…"
        return raw or f"HTTP {exc.code}"

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        """Map a provider-neutral :class:`LLMRequest` to an Ollama chat payload."""
        messages: list[dict[str, str]] = []

        system = request.system_instruction or self._system_instruction
        if system:
            messages.append({"role": "system", "content": system})

        messages.extend(self._conversation_messages(request.conversation))
        messages.append({"role": "user", "content": self._build_user_message(request)})

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }

        tools = self._build_tools(request.tool_definitions)
        if tools:
            payload["tools"] = tools

        if self._request_format:
            payload["format"] = self._request_format

        if self._options:
            payload["options"] = dict(self._options)

        return payload

    def _build_user_message(self, request: LLMRequest) -> str:
        """Build the user message text from the request and its context."""
        parts = [request.user_request]

        context: dict[str, object] = {}
        if request.intent:
            context["intent"] = request.intent
        if request.observations:
            context["observations"] = [
                getattr(obs, "result", obs) for obs in request.observations
            ]
        if request.verification:
            context["verification"] = [
                {
                    "action": getattr(rec, "action_name", None),
                    "trust": getattr(rec, "trust", None),
                }
                for rec in request.verification
            ]
        if request.state_summary:
            context["state"] = request.state_summary

        if context:
            parts.append(
                "\n\nContext:\n" + json.dumps(context, default=str, indent=2)
            )

        return "\n".join(parts)

    @staticmethod
    def _conversation_messages(
        conversation: tuple[ConversationTurn, ...],
    ) -> list[dict[str, str]]:
        """Map provider-neutral conversation turns to Ollama chat messages."""
        messages: list[dict[str, str]] = []
        for turn in conversation:
            role = turn.role if turn.role in ("user", "assistant", "system") else "user"
            messages.append({"role": role, "content": turn.content})
        return messages

    def _build_tools(self, tool_definitions: tuple[ToolDefinition, ...]) -> list[dict[str, Any]]:
        """Map provider-neutral tool definitions to Ollama's function-tool schema."""
        tools: list[dict[str, Any]] = []
        for definition in tool_definitions:
            properties: dict[str, dict[str, str]] = {}
            required: list[str] = []
            for arg in definition.arguments:
                properties[arg.name] = {
                    "type": arg.type,
                    "description": arg.description,
                }
                if arg.required:
                    required.append(arg.name)
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": definition.name,
                        "description": definition.description,
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    },
                }
            )
        return tools

    def _parse_response(self, data: dict[str, Any]) -> ModelResponse:
        """Map an Ollama ``/api/chat`` body to a provider-neutral response."""
        metadata = ModelMetadata(
            model_identifier=self.model_identifier,
            provider="ollama",
            usage={
                key: data[key]
                for key in ("eval_count", "prompt_eval_count", "total_duration")
                if key in data
            },
        )
        message = data.get("message")
        if not isinstance(message, dict):
            raise MalformedModelResponseError(
                "Ollama response has no message object"
            )
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            first = tool_calls[0]
            function = first.get("function", {}) if isinstance(first, dict) else {}
            name = function.get("name") if isinstance(function, dict) else None
            arguments = function.get("arguments") if isinstance(function, dict) else None
            if not isinstance(name, str) or not name.strip():
                raise InvalidModelResponseError(
                    "Ollama tool call is missing a function name"
                )
            if not isinstance(arguments, dict):
                raise InvalidModelResponseError(
                    "Ollama tool call arguments must be a structured mapping"
                )
            return ModelResponse.tool_call_request(
                name=name, arguments=arguments, metadata=metadata
            )
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise InvalidModelResponseError(
                "Ollama response has neither tool calls nor text content"
            )
        return ModelResponse.final_response(content=content, metadata=metadata)


def _indicates_context_length(detail: str) -> bool:
    """True when an Ollama error body clearly signals a context/token limit."""
    lowered = detail.lower()
    return any(phrase in lowered for phrase in _CONTEXT_LENGTH_PHRASES)