"""Live Ollama integration tests (skipped unless Ollama is reachable).

These tests require a running Ollama server with the configured model
loaded (default ``qwen3:1.7b``). They are intentionally excluded from the
deterministic unit-test path: run them explicitly, e.g.::

    uv run python -m unittest discover -s tests/integration

Set ``OLLAMA_MODEL`` to override the model under test.
"""

from __future__ import annotations

import os
import unittest
import urllib.request

MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:1.7b")
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def _ollama_reachable() -> bool:
    try:
        with urllib.request.urlopen(BASE_URL + "/", timeout=2) as _:
            return True
    except Exception:
        return False


@unittest.skipUnless(_ollama_reachable(), "Ollama server not reachable")
class TestLiveOllamaAdapter(unittest.TestCase):
    def test_live_final_response(self) -> None:
        from personal_finance_agent.llm import LLMRequest, OllamaLLMClient

        client = OllamaLLMClient(model=MODEL, base_url=BASE_URL, timeout=180.0)
        response = client.complete(
            LLMRequest(user_request="Reply with exactly: OK")
        )
        self.assertEqual(response.response_type, "final_response")
        assert response.content is not None
        self.assertTrue(response.content.strip())


if __name__ == "__main__":
    unittest.main()
