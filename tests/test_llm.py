"""Tests for the provider-neutral LLM abstraction and fake client.

Covers the LLM client interface, structured model responses, tool call
representation, the deterministic FakeLLMClient (including failure modes),
request/context representation, tool definitions, and the Agent Runtime
injection boundary.
"""

from __future__ import annotations

import unittest

from personal_finance_agent.llm import (
    DEFAULT_TOOL_DEFINITIONS,
    ConversationTurn,
    FakeLLMClient,
    InvalidModelResponseError,
    LLMRequest,
    LLMError,
    MalformedModelResponseError,
    ModelMetadata,
    ModelResponse,
    ModelTimeoutError,
    ModelUnavailableError,
    RESPONSE_TYPE_FINAL,
    RESPONSE_TYPE_TOOL_CALL,
    ResponseSequenceExhaustedError,
    ToolCall,
    tool_definition_for,
    validate_model_response,
)
from personal_finance_agent.runtime.agent import Agent, run
from personal_finance_agent.runtime.state import (
    Observation,
    VerificationRecord,
)
from personal_finance_agent.runtime.tools import TOOLS
from personal_finance_agent.verification import VerificationResult

from tests.support import standard_transactions


def _sample_request(
    *,
    observations: tuple[object, ...] = (),
    verification: tuple[object, ...] = (),
) -> LLMRequest:
    """Build a populated LLMRequest for context tests."""
    return LLMRequest(
        user_request="Why did my September spending increase?",
        intent="spending_change_explanation",
        tool_definitions=DEFAULT_TOOL_DEFINITIONS,
        observations=observations,
        verification=verification,
        conversation=(
            ConversationTurn(role="user", content="How much did I spend in August?"),
            ConversationTurn(role="assistant", content="Total for 2025-08."),
        ),
        system_instruction="You are a grounded personal-finance analysis agent.",
        state_summary={
            "periods": ("2025-09", "2025-08"),
            "completed_actions": ["period_comparison"],
        },
    )


# --- B. FakeLLMClient --------------------------------------------------------


class TestFakeLLMClient(unittest.TestCase):
    """B. FakeLLMClient: sequencing, recording, failure modes."""

    def test_sequential_responses_in_order(self) -> None:
        fake = FakeLLMClient(
            [
                FakeLLMClient.tool_call("period_comparison", {"period_b": "2025-09"}),
                FakeLLMClient.tool_call("category_analysis", {"period": "2025-09"}),
                FakeLLMClient.tool_call("merchant_analysis", {"period": "2025-09"}),
                FakeLLMClient.final_response("September increased due to Shopping."),
            ]
        )
        request = _sample_request()
        names = [fake.complete(request).tool_call.name for _ in range(3)]
        self.assertEqual(
            names, ["period_comparison", "category_analysis", "merchant_analysis"]
        )
        final = fake.complete(request)
        self.assertEqual(final.response_type, RESPONSE_TYPE_FINAL)
        self.assertEqual(final.content, "September increased due to Shopping.")

    def test_requests_recorded_with_context(self) -> None:
        fake = FakeLLMClient([FakeLLMClient.final_response("ok")])
        fake.complete(_sample_request())
        self.assertEqual(len(fake.requests), 1)
        recorded = fake.requests[0]
        self.assertEqual(
            recorded.user_request, "Why did my September spending increase?"
        )
        self.assertEqual(recorded.intent, "spending_change_explanation")
        self.assertEqual(recorded.tool_definitions, DEFAULT_TOOL_DEFINITIONS)

    def test_model_identifier(self) -> None:
        fake = FakeLLMClient()
        self.assertEqual(fake.model_identifier, "fake-llm-client")
        custom = FakeLLMClient(model_identifier="scripted-model-v1")
        self.assertEqual(custom.model_identifier, "scripted-model-v1")

    def test_exhausted_response_sequence(self) -> None:
        fake = FakeLLMClient([FakeLLMClient.final_response("ok")])
        fake.complete(_sample_request())
        self.assertEqual(fake.remaining, 0)
        with self.assertRaises(ResponseSequenceExhaustedError):
            fake.complete(_sample_request())
        # The failed call was still recorded.
        self.assertEqual(len(fake.requests), 2)

    def test_explicit_model_error_is_raised(self) -> None:
        fake = FakeLLMClient([ModelUnavailableError("provider down")])
        with self.assertRaises(ModelUnavailableError):
            fake.complete(_sample_request())
        # Subsequent calls also raise LLMError (sequence exhausted).
        with self.assertRaises(LLMError):
            fake.complete(_sample_request())

    def test_timeout_error_is_raised(self) -> None:
        fake = FakeLLMClient([ModelTimeoutError("timed out after 30s")])
        with self.assertRaises(ModelTimeoutError):
            fake.complete(_sample_request())

    def test_malformed_response_behavior(self) -> None:
        # A scripted non-ModelResponse simulates unparseable model output.
        fake = FakeLLMClient(["this is not structured output"])
        with self.assertRaises(MalformedModelResponseError):
            fake.complete(_sample_request())
        self.assertEqual(len(fake.requests), 1)

    def test_invalid_response_not_silently_corrected(self) -> None:
        # The fake returns an invalid response verbatim; validation must catch it.
        invalid = ModelResponse(response_type="bogus")
        fake = FakeLLMClient([invalid])
        returned = fake.complete(_sample_request())
        self.assertIs(returned, invalid)
        with self.assertRaises(InvalidModelResponseError):
            validate_model_response(returned)

    def test_reason_and_generate_response_consume_sequence(self) -> None:
        fake = FakeLLMClient(
            [
                FakeLLMClient.tool_call("period_comparison"),
                FakeLLMClient.final_response("done"),
            ]
        )
        self.assertEqual(
            fake.reason(_sample_request()).response_type, RESPONSE_TYPE_TOOL_CALL
        )
        self.assertEqual(
            fake.generate_response(_sample_request()).response_type, RESPONSE_TYPE_FINAL
        )
# --- C. Request / context representation -------------------------------------


class TestRequestContext(unittest.TestCase):
    """C. Context: request, tools, observations, verification, no raw data."""

    def test_user_request_represented(self) -> None:
        request = _sample_request()
        self.assertEqual(
            request.user_request, "Why did my September spending increase?"
        )
        self.assertEqual(request.intent, "spending_change_explanation")

    def test_tools_represented(self) -> None:
        definitions = _sample_request().tool_definitions
        names = [definition.name for definition in definitions]
        self.assertEqual(
            names,
            [
                "spending_summary",
                "category_analysis",
                "period_comparison",
                "merchant_analysis",
                "noteworthy_transactions",
            ],
        )
        comparison = tool_definition_for("period_comparison")
        self.assertIsNotNone(comparison)
        self.assertIn("period_a", [a.name for a in comparison.arguments])
        self.assertIn("period_b", [a.name for a in comparison.arguments])

    def test_observations_represented(self) -> None:
        observation = Observation(
            action_name="period_comparison",
            success=True,
            result={"total_a": "10", "total_b": "20"},
        )
        request = _sample_request(observations=(observation,))
        self.assertEqual(len(request.observations), 1)
        recorded = request.observations[0]
        self.assertEqual(recorded.action_name, "period_comparison")
        self.assertTrue(recorded.success)

    def test_verification_information_represented(self) -> None:
        verification = VerificationRecord(
            action_name="period_comparison",
            status="passed",
            trust="verified",
            detail=VerificationResult(
                target="period_comparison", status="passed", checks=()
            ),
        )
        request = _sample_request(verification=(verification,))
        self.assertEqual(len(request.verification), 1)
        self.assertEqual(request.verification[0].trust, "verified")

    def test_conversation_context_represented(self) -> None:
        request = _sample_request()
        self.assertEqual(len(request.conversation), 2)
        self.assertEqual(request.conversation[0].role, "user")

    def test_system_instruction_represented(self) -> None:
        request = _sample_request()
        self.assertIn("grounded", request.system_instruction)

    def test_raw_transactions_not_included(self) -> None:
        # LLMRequest has no field that can carry transaction records.
        request = _sample_request()
        field_names = set(request.__dataclass_fields__.keys())
        self.assertNotIn("transactions", field_names)
        self.assertNotIn("transactions", request.extra)
        self.assertNotIn("transactions", request.state_summary)

    def test_tool_definitions_match_registered_tools(self) -> None:
        registered = set(TOOLS.keys())
        described = {definition.name for definition in DEFAULT_TOOL_DEFINITIONS}
        self.assertEqual(described, registered)
# --- D. Agent Runtime injection boundary -------------------------------------


class TestRuntimeInjection(unittest.TestCase):
    """D. Runtime accepts/injects an LLM client without breaking determinism."""

    def test_default_deterministic_path_unchanged(self) -> None:
        transactions = standard_transactions()
        state = run("How much did I spend in August?", transactions)
        self.assertEqual(state.intent.value, "spending_summary")
        self.assertEqual(state.response_status.value, "verified")
        self.assertIsNone(state.model_identifier)
        self.assertIn("USD 400.00", state.response)

    def test_injected_client_does_not_break_execution(self) -> None:
        transactions = standard_transactions()
        fake = FakeLLMClient()
        state = run(
            "How much did I spend in August?",
            transactions,
            llm_client=fake,
        )
        self.assertEqual(state.intent.value, "spending_summary")
        self.assertEqual(state.response_status.value, "verified")
        self.assertEqual(state.model_identifier, "fake-llm-client")
        # Deterministic phase: the injected client is recorded, not called.
        self.assertEqual(fake.requests, [])

    def test_injected_result_matches_deterministic_result(self) -> None:
        transactions = standard_transactions()
        request = "Compare August and September spending."
        baseline = run(request, transactions)
        injected = run(request, transactions, llm_client=FakeLLMClient())
        self.assertEqual(baseline.response, injected.response)
        self.assertEqual(baseline.intent, injected.intent)
        self.assertEqual(
            [a.name for a in baseline.plan], [a.name for a in injected.plan]
        )
        self.assertEqual(
            baseline.verification_records, injected.verification_records
        )

    def test_agent_wrapper_accepts_client(self) -> None:
        transactions = standard_transactions()
        fake = FakeLLMClient()
        agent = Agent(transactions, llm_client=fake)
        self.assertTrue(agent.has_llm_client)
        state = agent.execute("What were my largest expenses in September?")
        self.assertEqual(state.model_identifier, "fake-llm-client")
        self.assertEqual(state.intent.value, "noteworthy_transactions")

    def test_agent_without_client_has_no_llm(self) -> None:
        agent = Agent(standard_transactions())
        self.assertFalse(agent.has_llm_client)
        self.assertIsNone(agent.llm_client)
        state = agent.execute("How much did I spend in August?")
        self.assertIsNone(state.model_identifier)

    def test_unsupported_request_with_client(self) -> None:
        # A client may be injected even when no request matches; no model call.
        fake = FakeLLMClient()
        state = run(
            "This request is not supported.",
            standard_transactions(),
            llm_client=fake,
        )
        self.assertEqual(state.response_status.value, "unsupported")
        self.assertEqual(state.model_identifier, "fake-llm-client")
        self.assertEqual(fake.requests, [])

    def test_custom_model_identifier_recorded(self) -> None:
        fake = FakeLLMClient(model_identifier="scripted-model-v1")
        state = run(
            "Compare August and September spending.",
            standard_transactions(),
            llm_client=fake,
        )
        self.assertEqual(state.model_identifier, "scripted-model-v1")


if __name__ == "__main__":
    unittest.main()