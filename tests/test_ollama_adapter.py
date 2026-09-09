"""Tests for the Ollama-backed LLMClient adapter.

All tests use a fake ``urlopen`` transport; no running Ollama server is
required. Live integration tests live separately under
``tests/integration/`` and are skipped when Ollama is unavailable.
"""

from __future__ import annotations

import io
import json
import socket
import unittest
import urllib.error
from unittest.mock import patch

from personal_finance_agent.llm import (
    DEFAULT_TOOL_DEFINITIONS,
    LLMRequest,
    OllamaLLMClient,
)
from personal_finance_agent.llm.errors import (
    ContextLengthError,
    InvalidModelResponseError,
    LLMError,
    MalformedModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)


def _request() -> LLMRequest:
    return LLMRequest(
        user_request="Why did my September spending increase?",
        intent="spending_change_explanation",
        tool_definitions=DEFAULT_TOOL_DEFINITIONS,
        system_instruction="You are a grounded agent.",
    )


def _tool_call_body() -> dict:
    return {
        "model": "qwen3:1.7b",
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "period_comparison",
                        "arguments": {"period_a": "2026-08", "period_b": "2026-09"},
                    }
                }
            ],
        },
        "done_reason": "tool_calls",
        "eval_count": 187,
        "prompt_eval_count": 42,
        "total_duration": 4420000000,
    }


def _final_body(content: str = "September spending rose.") -> dict:
    return {
        "model": "qwen3:1.7b",
        "message": {"role": "assistant", "content": content},
        "done_reason": "stop",
        "eval_count": 100,
    }


class _FakeHTTPResponse:
    """Minimal context-manager stub for ``urllib.request.urlopen``."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _json_response(body: dict) -> _FakeHTTPResponse:
    return _FakeHTTPResponse(json.dumps(body).encode("utf-8"))


class TestOllamaAdapterRequest(unittest.TestCase):
    def test_model_identifier(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        self.assertEqual(client.model_identifier, "ollama:qwen3:1.7b")

    def test_request_construction(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b", options={"temperature": 0})
        captured: dict = {}

        def fake_urlopen(request: object, timeout: object = None) -> _FakeHTTPResponse:
            captured["url"] = request.full_url  # type: ignore[union-attr]
            captured["payload"] = json.loads(request.data.decode("utf-8"))  # type: ignore[union-attr]
            captured["timeout"] = timeout
            return _json_response(_final_body())

        with patch("urllib.request.urlopen", fake_urlopen):
            client.complete(_request())

        self.assertEqual(captured["url"], "http://localhost:11434/api/chat")
        payload = captured["payload"]
        self.assertEqual(payload["model"], "qwen3:1.7b")
        self.assertIs(payload["stream"], False)
        self.assertEqual(payload["options"], {"temperature": 0})
        roles = [message["role"] for message in payload["messages"]]
        self.assertEqual(roles[0], "system")
        self.assertEqual(roles[-1], "user")

    def test_tool_schema_conversion(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        captured: dict = {}

        def fake_urlopen(request: object, timeout: object = None) -> _FakeHTTPResponse:
            captured["payload"] = json.loads(request.data.decode("utf-8"))  # type: ignore[union-attr]
            return _json_response(_final_body())

        with patch("urllib.request.urlopen", fake_urlopen):
            client.complete(_request())

        tools = captured["payload"]["tools"]
        self.assertEqual(len(tools), len(DEFAULT_TOOL_DEFINITIONS))
        by_name = {tool["function"]["name"]: tool for tool in tools}
        comparison = by_name["period_comparison"]["function"]
        self.assertEqual(comparison["parameters"]["type"], "object")
        self.assertIn("period_a", comparison["parameters"]["required"])
        for tool in tools:
            self.assertEqual(tool["type"], "function")

    def test_format_omitted_by_default(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        captured: dict = {}

        def fake_urlopen(request: object, timeout: object = None) -> _FakeHTTPResponse:
            captured["payload"] = json.loads(request.data.decode("utf-8"))  # type: ignore[union-attr]
            return _json_response(_final_body())

        with patch("urllib.request.urlopen", fake_urlopen):
            client.complete(_request())
        self.assertNotIn("format", captured["payload"])

    def test_format_included_when_requested(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b", request_format="json")
        captured: dict = {}

        def fake_urlopen(request: object, timeout: object = None) -> _FakeHTTPResponse:
            captured["payload"] = json.loads(request.data.decode("utf-8"))  # type: ignore[union-attr]
            return _json_response(_final_body())

        with patch("urllib.request.urlopen", fake_urlopen):
            client.complete(_request())
        self.assertEqual(captured["payload"]["format"], "json")

    def test_rejects_empty_model(self) -> None:
        with self.assertRaises(ValueError):
            OllamaLLMClient(model="")

    def test_default_timeout_is_120(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        captured: dict = {}

        def fake_urlopen(request: object, timeout: object = None) -> _FakeHTTPResponse:
            captured["timeout"] = timeout
            return _json_response(_final_body())

        with patch("urllib.request.urlopen", fake_urlopen):
            client.complete(_request())
        self.assertEqual(captured["timeout"], 120.0)

    def test_conversation_turns_become_messages(self) -> None:
        from personal_finance_agent.llm import ConversationTurn

        client = OllamaLLMClient(model="qwen3:1.7b")
        captured: dict = {}
        history_request = LLMRequest(
            user_request="What about August?",
            conversation=(ConversationTurn(role="user", content="September?"),),
        )

        def fake_urlopen(req: object, timeout: object = None) -> _FakeHTTPResponse:
            captured["payload"] = json.loads(req.data.decode("utf-8"))  # type: ignore[union-attr]
            return _json_response(_final_body())

        with patch("urllib.request.urlopen", fake_urlopen):
            client.complete(history_request)
        roles = [message["role"] for message in captured["payload"]["messages"]]
        self.assertEqual(roles, ["user", "user"])

class TestOllamaAdapterResponse(unittest.TestCase):
    def test_tool_call_mapping(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        with patch("urllib.request.urlopen", lambda *a, **k: _json_response(_tool_call_body())):
            response = client.complete(_request())
        self.assertEqual(response.response_type, "tool_call")
        assert response.tool_call is not None
        self.assertEqual(response.tool_call.name, "period_comparison")
        self.assertEqual(response.tool_call.arguments, {"period_a": "2026-08", "period_b": "2026-09"})
        assert response.metadata is not None
        self.assertEqual(response.metadata.model_identifier, "ollama:qwen3:1.7b")
        self.assertEqual(response.metadata.provider, "ollama")
        self.assertEqual(response.metadata.usage.get("eval_count"), 187)

    def test_final_response_mapping(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        with patch("urllib.request.urlopen", lambda *a, **k: _json_response(_final_body("Done."))):
            response = client.complete(_request())
        self.assertEqual(response.response_type, "final_response")
        self.assertEqual(response.content, "Done.")

    def test_malformed_json(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        with patch("urllib.request.urlopen", lambda *a, **k: _FakeHTTPResponse(b"not json{")):
            with self.assertRaises(MalformedModelResponseError):
                client.complete(_request())

    def test_empty_content_invalid(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        with patch("urllib.request.urlopen", lambda *a, **k: _json_response(_final_body("   "))):
            with self.assertRaises(InvalidModelResponseError):
                client.complete(_request())

    def test_tool_call_missing_name_invalid(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        body = _tool_call_body()
        body["message"]["tool_calls"][0]["function"].pop("name")
        with patch("urllib.request.urlopen", lambda *a, **k: _json_response(body)):
            with self.assertRaises((InvalidModelResponseError, LLMError)):
                client.complete(_request())


class TestOllamaAdapterErrors(unittest.TestCase):
    def test_connection_refused(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            with self.assertRaises(ModelUnavailableError):
                client.complete(_request())

    def test_timeout(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
            with self.assertRaises(ModelTimeoutError):
                client.complete(_request())

    def test_generic_http_500(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        error = urllib.error.HTTPError(
            "http://localhost:11434/api/chat", 500, "err", {}, io.BytesIO(b"boom"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ModelUnavailableError):
                client.complete(_request())

    def test_generic_http_400_not_context_length(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        error = urllib.error.HTTPError(
            "http://localhost:11434/api/chat", 400, "err", {}, io.BytesIO(b"bad model"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ModelUnavailableError) as ctx:
                client.complete(_request())
        self.assertNotIsInstance(ctx.exception, ContextLengthError)

    def test_context_length_http_400(self) -> None:
        client = OllamaLLMClient(model="qwen3:1.7b")
        error = urllib.error.HTTPError(
            "http://localhost:11434/api/chat", 400, "err", {},
            io.BytesIO(b"prompt exceeds context length of model"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(ContextLengthError):
                client.complete(_request())


if __name__ == "__main__":
    unittest.main()

