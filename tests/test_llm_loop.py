"""Deterministic tests for the LLM-driven agent loop (DEC-023).

Uses FakeLLMClient; no live model required.

Budgets: max_model_steps=6, max_tool_calls=4, max_consecutive_repeats=2,
retry_invalid=1 (see LLMLoopConfig).

Reversed periods (DEC-023): period_comparison with period_a > period_b is
REJECTED at semantic validation (not normalized); order is semantically
meaningful (absolute_difference = total_b - total_a).

Grounding (MVP): currency-anchored figures (e.g. "USD 400.00") must match
verified observations. Correct number + wrong explanation may still pass.
"""

from __future__ import annotations

import unittest

from personal_finance_agent.llm import (
    FakeLLMClient,
    ModelResponse,
    ModelTimeoutError,
    ModelUnavailableError,
    ToolCall,
)
from personal_finance_agent.llm.errors import ResponseSequenceExhaustedError
from personal_finance_agent.runtime.agent import run
from personal_finance_agent.runtime.llm_loop import (
    LLMLoopConfig,
    LLMTerminationReason,
    build_llm_request,
    grounding_gate,
    run_llm_loop,
    summarise_observation_for_llm,
    validate_llm_tool_call,
)
from personal_finance_agent.runtime.state import AgentState, Observation, ResponseStatus

from tests.support import standard_transactions


def _tx() -> list:
    return standard_transactions()


def _tool(name: str, args: dict | None = None) -> ModelResponse:
    return ModelResponse.tool_call_request(name=name, arguments=args or {})


def _final(content: str) -> ModelResponse:
    return ModelResponse.final_response(content=content)


class TestSingleToolCall(unittest.TestCase):
    def test_single_tool_executes_and_produces_final(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _final("Total spending in August was USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value
        )
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        self.assertIn("USD 400.00", state.response)
        self.assertEqual(fake.remaining, 0)
        self.assertIn("spending_summary", [o.action_name for o in state.observations])
        self.assertTrue(state.verified("spending_summary"))


class TestMultipleToolCalls(unittest.TestCase):
    def test_two_tools_then_final(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("period_comparison",
                      {"period_a": "2025-08", "period_b": "2025-09"}),
                _tool("merchant_analysis", {"period": "2025-09"}),
                _final("Spending rose from USD 400.00 to USD 780.00. "
                       "Top merchant OnlineShop USD 700.00."),
            ]
        )
        state = run_llm_loop(
            "Why did my spending increase in September?", _tx(), fake)
        names = [o.action_name for o in state.observations if o.success]
        self.assertIn("period_comparison", names)
        self.assertIn("merchant_analysis", names)
        self.assertTrue(state.verified("period_comparison"))
        self.assertTrue(state.verified("merchant_analysis"))


class TestReplanning(unittest.TestCase):
    def test_model_drives_two_distinct_tools(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _tool("merchant_analysis", {"period": "2025-08"}),
                _final("August total USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        names = [o.action_name for o in state.observations if o.success]
        self.assertEqual(names[0], "spending_summary")
        self.assertIn("merchant_analysis", names)
        self.assertGreaterEqual(len(fake.requests), 3)
        self.assertGreaterEqual(len(fake.requests[1].observations), 1)

class TestUnknownTool(unittest.TestCase):
    def test_unknown_tool_then_recovery(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("no_such_tool", {"period": "2025-08"}),
                _tool("spending_summary", {"period": "2025-08"}),
                _final("August total USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        self.assertIn("USD 400.00", state.response)
        self.assertTrue(any("no_such_tool" in e for e in state.errors))

    def test_unknown_tool_exhausts_retry(self) -> None:
        fake = FakeLLMClient(
            [_tool("no_such_tool", {}), _tool("bogus", {})])
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason,
            LLMTerminationReason.MAX_RETRIES_INVALID.value)
        self.assertEqual(state.response_status, ResponseStatus.ERROR)
        self.assertIn("trouble", state.response)


class TestInvalidArgs(unittest.TestCase):
    def test_missing_required_arg_then_recovery(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {}),
                _tool("spending_summary", {"period": "2025-08"}),
                _final("August total USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)

    def test_unexpected_arg_rejected(self) -> None:
        v = validate_llm_tool_call(
            ToolCall(name="spending_summary",
                     arguments={"period": "2025-08", "bogus": 1}))
        self.assertFalse(v.passed)
        self.assertEqual(v.layer, "contract")


class TestInvalidPeriodFormat(unittest.TestCase):
    def test_bad_period_format_rejected_at_semantic_layer(self) -> None:
        v = validate_llm_tool_call(
            ToolCall(name="spending_summary",
                     arguments={"period": "August 2025"}))
        self.assertFalse(v.passed)
        self.assertEqual(v.layer, "semantic")

    def test_bad_period_then_recovery_in_loop(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "August 2025"}),
                _tool("spending_summary", {"period": "2025-08"}),
                _final("August total USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)


class TestReversedPeriods(unittest.TestCase):
    def test_reversed_periods_rejected_deterministically(self) -> None:
        v = validate_llm_tool_call(
            ToolCall(name="period_comparison",
                     arguments={"period_a": "2025-09", "period_b": "2025-08"}))
        self.assertFalse(v.passed)
        self.assertEqual(v.layer, "semantic")
        self.assertIn("period_a", v.reason)

    def test_reversed_periods_do_not_execute_then_model_recovers(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("period_comparison",
                      {"period_a": "2025-09", "period_b": "2025-08"}),
                _tool("period_comparison",
                      {"period_a": "2025-08", "period_b": "2025-09"}),
                _final("Spending rose from USD 400.00 to USD 780.00, "
                       "up USD 380.00."),
            ]
        )
        state = run_llm_loop("Compare August and September spending.",
                             _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        obs = [o for o in state.observations if o.success]
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0].action_name, "period_comparison")
        result = obs[0].result
        self.assertEqual(str(result.total_a), "400.00")
        self.assertEqual(str(result.total_b), "780.00")
class TestMalformedResponse(unittest.TestCase):
    def test_malformed_entry_then_recovery(self) -> None:
        fake = FakeLLMClient(
            [
                "not a model response",
                _tool("spending_summary", {"period": "2025-08"}),
                _final("August total USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        self.assertIn("USD 400.00", state.response)

    def test_malformed_exhausts_retry(self) -> None:
        fake = FakeLLMClient(["junk-1", "junk-2"])
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason,
            LLMTerminationReason.MAX_RETRIES_INVALID.value)
        self.assertEqual(state.response_status, ResponseStatus.ERROR)


class TestEmptyFinalResponse(unittest.TestCase):
    def test_empty_final_is_invalid_but_model_may_retry(self) -> None:
        bad = ModelResponse(response_type="final_response", content="  ",
                            tool_call=None)
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                bad,
                _final("August total USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertIn("USD 400.00", state.response)


class TestGroundingRejectsUnsupportedFigure(unittest.TestCase):
    def test_unsupported_figure_falls_back_deterministically(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _final("Total spending in August was USD 999.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.GROUNDING_FALLBACK.value)
        self.assertEqual(state.response_status, ResponseStatus.INCOMPLETE)
        self.assertNotIn("999.00", state.response)
        self.assertIn("USD 400.00", state.response)

    def test_grounding_gate_directly(self) -> None:
        state = AgentState(request="q")
        from personal_finance_agent.analytics import spending_summary
        from personal_finance_agent.models import Period
        import datetime as _dt
        period = Period(_dt.date(2025, 8, 1), _dt.date(2025, 8, 31), "2025-08")
        result = spending_summary(_tx(), period)
        state.observations.append(
            Observation(action_name="spending_summary", success=True,
                        result=result))
        from personal_finance_agent.runtime.state import VerificationRecord
        state.verification_records.append(
            VerificationRecord(action_name="spending_summary", status="passed",
                               trust="verified", detail=None))
        gate = grounding_gate("August total USD 400.00.", state)
        self.assertTrue(gate.passed)
        gate2 = grounding_gate("August total USD 999.00.", state)
        self.assertFalse(gate2.passed)


class TestFailedVerification(unittest.TestCase):
    def test_genuinely_failed_verification_is_recorded(self) -> None:
        from unittest.mock import patch
        from personal_finance_agent.verification import VerificationResult
        from personal_finance_agent.verification import CheckResult
        bad_detail = VerificationResult(
            target="spending_summary", status="failed",
            checks=(CheckResult(name="total", passed=False, message="tampered",
                                expected="400", actual="0"),))
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _final("Summary for August."),
            ]
        )
        with patch("personal_finance_agent.runtime.llm_loop.verify_for",
                   return_value=("failed", bad_detail)):
            state = run_llm_loop(
                "How much did I spend in August?", _tx(), fake)
        trusts = [r.trust for r in state.verification_records]
        self.assertIn("failed", trusts)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertIn("Summary for August.", state.response)


class TestInconclusiveVerification(unittest.TestCase):
    def test_inconclusive_verification_recorded(self) -> None:
        from unittest.mock import patch
        from personal_finance_agent.verification import VerificationResult
        detail = VerificationResult(target="spending_summary",
                                    status="inconclusive", checks=())
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _final("Summary for August."),
            ]
        )
        with patch("personal_finance_agent.runtime.llm_loop.verify_for",
                   return_value=("inconclusive", detail)):
            state = run_llm_loop(
                "How much did I spend in August?", _tx(), fake)
        self.assertIn("inconclusive",
                      [r.trust for r in state.verification_records])

class TestModelErrors(unittest.TestCase):
    def test_model_timeout_terminates_safely(self) -> None:
        fake = FakeLLMClient([ModelTimeoutError("timed out")])
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.MODEL_ERROR.value)
        self.assertEqual(state.response_status, ResponseStatus.ERROR)
        self.assertTrue(state.response)

    def test_model_unavailable_terminates_safely(self) -> None:
        fake = FakeLLMClient([ModelUnavailableError("down")])
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.MODEL_ERROR.value)
        self.assertEqual(state.response_status, ResponseStatus.ERROR)

    def test_exhausted_responses_terminates_safely(self) -> None:
        fake = FakeLLMClient([])
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.MODEL_ERROR.value)
        self.assertEqual(state.response_status, ResponseStatus.ERROR)
        self.assertTrue(state.response)


class TestBudgets(unittest.TestCase):
    def test_model_step_budget(self) -> None:
        fake = FakeLLMClient(
            [_tool("spending_summary", {"period": "2025-08"})] * 10)
        cfg = LLMLoopConfig(max_model_steps=2, max_tool_calls=10,
                            max_consecutive_repeats=10, retry_invalid=1)
        state = run_llm_loop("How much did I spend in August?", _tx(), fake,
                             cfg)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.BUDGET_STEPS.value)
        self.assertEqual(state.response_status, ResponseStatus.INCOMPLETE)

    def test_tool_call_budget(self) -> None:
        fake = FakeLLMClient(
            [_tool("spending_summary", {"period": "2025-08"})] * 10)
        cfg = LLMLoopConfig(max_model_steps=10, max_tool_calls=1,
                            max_consecutive_repeats=10, retry_invalid=1)
        state = run_llm_loop("How much did I spend in August?", _tx(), fake,
                             cfg)
        self.assertIn(
            state.termination_reason,
            (LLMTerminationReason.BUDGET_TOOL_CALLS.value,
             LLMTerminationReason.BUDGET_STEPS.value,
             LLMTerminationReason.MAX_CONSECUTIVE_REPEATS.value))
        self.assertEqual(state.response_status, ResponseStatus.INCOMPLETE)
        self.assertLessEqual(state.tool_calls_used, 2)


class TestRepeatedToolCall(unittest.TestCase):
    def test_repeated_identical_calls_bounded(self) -> None:
        cfg = LLMLoopConfig(max_model_steps=6, max_tool_calls=6,
                            max_consecutive_repeats=2, retry_invalid=5)
        fake = FakeLLMClient(
            [_tool("spending_summary", {"period": "2025-08"})] * 6)
        state = run_llm_loop("How much did I spend in August?", _tx(), fake,
                             cfg)
        self.assertEqual(
            state.termination_reason,
            LLMTerminationReason.MAX_CONSECUTIVE_REPEATS.value)
        self.assertEqual(state.response_status, ResponseStatus.INCOMPLETE)
        self.assertEqual(state.tool_calls_used, 2)

    def test_distinct_args_do_not_trigger_repeat_bound(self) -> None:
        cfg = LLMLoopConfig(max_model_steps=6, max_tool_calls=6,
                            max_consecutive_repeats=2, retry_invalid=5)
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _tool("category_analysis", {"period": "2025-08"}),
                _final("August total USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake,
                             cfg)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)

class TestGroundedFinalResponse(unittest.TestCase):
    def test_grounded_final_passes_through(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _final("Total spending in August was USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        self.assertEqual(state.response,
                         "Total spending in August was USD 400.00.")

    def test_ungrounded_figure_triggers_fallback(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _final("Total spending in August was USD 1234.56."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.GROUNDING_FALLBACK.value)
        self.assertEqual(state.response_status, ResponseStatus.INCOMPLETE)
        self.assertNotIn("1234.56", state.response)

    def test_correct_number_wrong_explanation_may_pass(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _final("August spending USD 400.00 was caused by aliens."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.RESPONSE_COMPLETE.value)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)


class TestUnsupportedAndAmbiguous(unittest.TestCase):
    def test_unsupported_request_terminates_with_status(self) -> None:
        fake = FakeLLMClient([_final("I can't help with that.")])
        state = run_llm_loop(
            "Should I invest in Bitcoin?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.UNSUPPORTED.value)
        self.assertEqual(state.response_status, ResponseStatus.UNSUPPORTED)

    def test_ambiguous_request_terminates_with_status(self) -> None:
        fake = FakeLLMClient([_final("Could you clarify?")])
        state = run_llm_loop(
            "How much did I spend recently?", _tx(), fake)
        self.assertEqual(
            state.termination_reason, LLMTerminationReason.AMBIGUOUS.value)
        self.assertEqual(state.response_status, ResponseStatus.AMBIGUOUS)


class TestProviderNeutrality(unittest.TestCase):
    def test_loop_uses_llmclient_abstraction(self) -> None:
        from personal_finance_agent.llm import LLMClient
        import inspect
        from personal_finance_agent.runtime import llm_loop as mod
        src = inspect.getsource(mod.run_llm_loop)
        self.assertNotIn("Ollama", src)
        self.assertNotIn("ollama", src)
        sig = inspect.signature(mod.run_llm_loop)
        ann = str(sig.parameters["llm_client"].annotation)
        self.assertIn("LLMClient", ann)

    def test_fake_client_needs_no_ollama(self) -> None:
        import sys
        self.assertNotIn("ollama", sys.modules)
        fake = FakeLLMClient([_final("No tools needed.")])
        state = run_llm_loop(
            "How much did I spend in August?", _tx(), fake)
        self.assertTrue(state.response)


class TestHybridPendingActions(unittest.TestCase):
    def test_matching_pending_action_consumed_no_duplicate(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("spending_summary", {"period": "2025-08"}),
                _final("August total USD 400.00."),
            ]
        )
        state = run_llm_loop("How much did I spend in August?", _tx(), fake)
        names = [o.action_name for o in state.observations if o.success]
        self.assertEqual(names.count("spending_summary"), 1)
        self.assertEqual(state.pending_actions, [])

    def test_unproposed_pending_action_gap_filled_with_verification(self) -> None:
        fake = FakeLLMClient(
            [
                _tool("period_comparison",
                      {"period_a": "2025-08", "period_b": "2025-09"}),
                _final("Spending rose from USD 400.00 to USD 780.00, "
                       "up USD 380.00."),
            ]
        )
        state = run_llm_loop(
            "Why did my spending increase in September?", _tx(), fake)
        names = [o.action_name for o in state.observations if o.success]
        self.assertIn("period_comparison", names)
        gap_filled = [n for n in names if n != "period_comparison"]
        self.assertTrue(len(gap_filled) >= 1)
        for obs in state.observations:
            if obs.success:
                self.assertTrue(
                    any(r.action_name == obs.action_name
                        for r in state.verification_records))


class TestDeterministicRunRegression(unittest.TestCase):
    def test_deterministic_run_unchanged(self) -> None:
        state = run("How much did I spend in August?", _tx())
        self.assertEqual(state.intent.value, "spending_summary")
        self.assertIn("USD 400.00", state.response)
        self.assertIsNone(state.model_identifier)
        self.assertIsNone(state.termination_reason)


class TestBuildRequestAndSummaries(unittest.TestCase):
    def test_build_request_has_no_raw_transactions(self) -> None:
        from dataclasses import astuple
        state = AgentState(request="q")
        req = build_llm_request("q", state, [], [], [], LLMLoopConfig())
        dumped = (
            str(astuple(req)) + str(req.state_summary) + str(req.extra))
        self.assertNotIn("FreshMart", dumped)
        self.assertEqual(len(req.tool_definitions), 5)

    def test_summarise_observation_hides_raw_rows(self) -> None:
        from personal_finance_agent.analytics import spending_summary
        from personal_finance_agent.models import Period
        import datetime as _dt
        period = Period(_dt.date(2025, 8, 1), _dt.date(2025, 8, 31), "2025-08")
        result = spending_summary(_tx(), period)
        obs = Observation(action_name="spending_summary", success=True,
                          result=result)
        summary = summarise_observation_for_llm(obs)
        self.assertNotIn("transactions", str(summary))
        self.assertEqual(summary["action_name"], "spending_summary")


if __name__ == "__main__":
    unittest.main()

