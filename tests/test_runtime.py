"""Tests for the deterministic agent runtime.

Covers the full lifecycle: understanding, planning, tool execution, state
management, verification integration, replanning, response generation, and
end-to-end agent execution against the synthetic dataset.
"""

from __future__ import annotations

import datetime as _dt
import unittest
from decimal import Decimal

from personal_finance_agent.models import Direction, Period, Transaction
from personal_finance_agent.runtime.agent import Agent, run
from personal_finance_agent.runtime.checks import (
    TRUST_FAILED,
    TRUST_INCONCLUSIVE,
    TRUST_UNVERIFIED,
    TRUST_VERIFIED,
    classify_trust,
    verify_for,
)
from personal_finance_agent.runtime.planning import plan_for
from personal_finance_agent.runtime.replanning import decide_followups
from personal_finance_agent.runtime.response import generate_response
from personal_finance_agent.runtime.state import (
    Action,
    AgentState,
    Intent,
    IntentStatus,
    ResponseStatus,
    TrajectoryStage,
)
from personal_finance_agent.runtime.tools import (
    ToolError,
    execute_tool,
    tool_for,
)
from personal_finance_agent.runtime.understanding import (
    DEFAULT_YEAR,
    UnderstandResult,
    understand,
)
from personal_finance_agent.verification import VerificationResult

from tests.support import AUGUST, SEPTEMBER, standard_transactions, tx
# --- A. Request understanding -------------------------------------------------


class TestUnderstanding(unittest.TestCase):
    """A. Request understanding: supported, unsupported, ambiguous."""

    def test_spending_summary_intent(self) -> None:
        result = understand("How much did I spend in August?")
        self.assertEqual(result.intent, Intent.SPENDING_SUMMARY)
        self.assertEqual(result.intent_status, IntentStatus.RECOGNIZED)
        self.assertTrue(any(p.label == "2025-08" for p in result.periods))

    def test_category_intent(self) -> None:
        result = understand("Show me spending by category for September")
        self.assertEqual(result.intent, Intent.CATEGORY_ANALYSIS)
        self.assertEqual(result.intent_status, IntentStatus.RECOGNIZED)

    def test_comparison_intent(self) -> None:
        result = understand("Compare August and September spending")
        self.assertEqual(result.intent, Intent.PERIOD_COMPARISON)
        self.assertEqual(result.intent_status, IntentStatus.RECOGNIZED)

    def test_merchant_intent(self) -> None:
        result = understand("Which merchants did I spend the most on in August?")
        self.assertEqual(result.intent, Intent.MERCHANT_ANALYSIS)
        self.assertEqual(result.intent_status, IntentStatus.RECOGNIZED)

    def test_noteworthy_intent(self) -> None:
        result = understand("What were my largest expenses in September?")
        self.assertEqual(result.intent, Intent.NOTEWORTHY_TRANSACTIONS)
        self.assertEqual(result.intent_status, IntentStatus.RECOGNIZED)

    def test_spending_change_intent(self) -> None:
        result = understand("Why did my spending increase in September?")
        self.assertEqual(result.intent, Intent.SPENDING_CHANGE_EXPLANATION)
        self.assertEqual(result.intent_status, IntentStatus.RECOGNIZED)

    def test_unsupported_request(self) -> None:
        result = understand("What is the meaning of life?")
        self.assertEqual(result.intent, Intent.UNSUPPORTED)
        self.assertEqual(result.intent_status, IntentStatus.UNSUPPORTED)

    def test_ambiguous_request(self) -> None:
        result = understand("How much did I spend?")
        self.assertEqual(result.intent, Intent.AMBIGUOUS)
        self.assertEqual(result.intent_status, IntentStatus.AMBIGUOUS)

    def test_empty_request(self) -> None:
        result = understand("")
        self.assertEqual(result.intent_status, IntentStatus.UNSUPPORTED)

    def test_bare_month_resolves(self) -> None:
        result = understand("spending summary for august")
        self.assertEqual(result.intent, Intent.SPENDING_SUMMARY)
        self.assertEqual(result.intent_status, IntentStatus.RECOGNIZED)
        self.assertEqual(result.periods[0], Period.for_month(DEFAULT_YEAR, 8))
# --- B. Planning --------------------------------------------------------------


class TestPlanning(unittest.TestCase):
    """B. Planning: correct plan for simple intents, multi-step for change."""

    def _understanding(self, intent: Intent, *periods) -> UnderstandResult:
        return UnderstandResult(
            intent=intent,
            intent_status=IntentStatus.RECOGNIZED,
            periods=periods,
        )

    def test_spending_summary_plan(self) -> None:
        u = self._understanding(Intent.SPENDING_SUMMARY, AUGUST)
        plan = plan_for(u)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].name, "spending_summary")
        self.assertEqual(plan[0].params["period"], AUGUST)

    def test_category_plan(self) -> None:
        u = self._understanding(Intent.CATEGORY_ANALYSIS, SEPTEMBER)
        plan = plan_for(u)
        self.assertEqual(plan[0].name, "category_analysis")
        self.assertEqual(plan[0].params["period"], SEPTEMBER)

    def test_comparison_plan_two_periods(self) -> None:
        u = self._understanding(Intent.PERIOD_COMPARISON, AUGUST, SEPTEMBER)
        plan = plan_for(u)
        self.assertEqual(plan[0].name, "period_comparison")
        self.assertEqual(plan[0].params["period_a"], AUGUST)
        self.assertEqual(plan[0].params["period_b"], SEPTEMBER)

    def test_merchant_plan(self) -> None:
        u = self._understanding(Intent.MERCHANT_ANALYSIS, AUGUST)
        plan = plan_for(u)
        self.assertEqual(plan[0].name, "merchant_analysis")

    def test_noteworthy_plan_has_limit(self) -> None:
        u = self._understanding(Intent.NOTEWORTHY_TRANSACTIONS, AUGUST)
        plan = plan_for(u)
        self.assertEqual(plan[0].name, "noteworthy_transactions")
        self.assertEqual(plan[0].params["limit"], 5)

    def test_spending_change_two_periods(self) -> None:
        u = self._understanding(
            Intent.SPENDING_CHANGE_EXPLANATION, AUGUST, SEPTEMBER
        )
        plan = plan_for(u)
        names = [a.name for a in plan]
        self.assertEqual(
            names,
            ["period_comparison", "category_analysis", "merchant_analysis"],
        )

    def test_spending_change_single_period(self) -> None:
        u = self._understanding(Intent.SPENDING_CHANGE_EXPLANATION, SEPTEMBER)
        plan = plan_for(u)
        names = [a.name for a in plan]
        self.assertIn("period_comparison", names)
        self.assertIn("category_analysis", names)
        self.assertIn("merchant_analysis", names)

    def test_empty_plan_for_unsupported(self) -> None:
        u = self._understanding(Intent.UNSUPPORTED)
        self.assertEqual(plan_for(u), ())
# --- C. Tool execution -------------------------------------------------------


class TestToolExecution(unittest.TestCase):
    """C. Tool execution: dispatch, valid execution, invalid action, errors."""

    def test_correct_tool_selected(self) -> None:
        tool = tool_for("spending_summary")
        self.assertEqual(tool.__name__, "_spending_summary")

    def test_valid_spending_summary_execution(self) -> None:
        transactions = standard_transactions()
        result = execute_tool(
            "spending_summary",
            {"transactions": transactions, "period": AUGUST, "currency": "USD"},
        )
        self.assertEqual(result.total, Decimal("400.00"))
        self.assertEqual(result.period, AUGUST)

    def test_invalid_action_raises_tool_error(self) -> None:
        with self.assertRaises(ToolError):
            tool_for("nonexistent_tool")

    def test_unknown_tool_execution_raises(self) -> None:
        with self.assertRaises(ToolError):
            execute_tool("nonexistent_tool", {})

    def test_missing_period_raises_tool_error(self) -> None:
        with self.assertRaises(ToolError):
            execute_tool("spending_summary", {"transactions": []})

    def test_category_tool_returns_analysis(self) -> None:
        transactions = standard_transactions()
        result = execute_tool(
            "category_analysis",
            {"transactions": transactions, "period": AUGUST, "currency": "USD"},
        )
        self.assertEqual(result.total_spending, Decimal("400.00"))
        self.assertGreater(len(result.category_totals), 0)
# --- D. State management ------------------------------------------------------


class TestStateManagement(unittest.TestCase):
    """D. State: updates after actions, observations, trajectory."""

    def test_state_initial_values(self) -> None:
        state = AgentState(request="test")
        self.assertEqual(state.response_status, ResponseStatus.PENDING)
        self.assertEqual(state.intent, Intent.UNSUPPORTED)
        self.assertEqual(state.observations, [])

    def test_trajectory_records_stages(self) -> None:
        state = AgentState(request="test")
        state.record(TrajectoryStage.RECEIVED, "received request")
        state.record(TrajectoryStage.UNDERSTAND, "understood")
        self.assertEqual(len(state.trajectory), 2)
        self.assertEqual(state.trajectory[0].stage, TrajectoryStage.RECEIVED)

    def test_observation_lookup(self) -> None:
        from personal_finance_agent.runtime.state import Observation

        state = AgentState(request="test")
        obs = Observation(action_name="spending_summary", success=True, result="x")
        state.observations.append(obs)
        self.assertIsNotNone(state.observation_for("spending_summary"))
        self.assertIsNone(state.observation_for("category_analysis"))

    def test_verified_helper(self) -> None:
        from personal_finance_agent.runtime.state import VerificationRecord

        state = AgentState(request="test")
        state.verification_records.append(
            VerificationRecord(
                action_name="spending_summary",
                status="passed",
                trust=TRUST_VERIFIED,
            )
        )
        self.assertTrue(state.verified("spending_summary"))
        self.assertFalse(state.verified("category_analysis"))
# --- E. Verification integration ----------------------------------------------


class TestVerificationIntegration(unittest.TestCase):
    """E. Verification: verified continues, failed not trusted, inconclusive."""

    def test_classify_trust_passed(self) -> None:
        v = VerificationResult(target="x", status="passed", checks=())
        self.assertEqual(classify_trust(v), TRUST_VERIFIED)

    def test_classify_trust_failed(self) -> None:
        v = VerificationResult(target="x", status="failed", checks=())
        self.assertEqual(classify_trust(v), TRUST_FAILED)

    def test_classify_trust_inconclusive(self) -> None:
        v = VerificationResult(target="x", status="inconclusive", checks=())
        self.assertEqual(classify_trust(v), TRUST_INCONCLUSIVE)

    def test_verify_for_spending_summary_passes(self) -> None:
        from personal_finance_agent.analytics import spending_summary

        transactions = standard_transactions()
        result = spending_summary(transactions, AUGUST, currency="USD")
        trust, detail = verify_for("spending_summary", result, transactions)
        self.assertEqual(trust, TRUST_VERIFIED)
        self.assertIsNotNone(detail)
        self.assertEqual(detail.status, "passed")

    def test_verify_for_unregistered_tool(self) -> None:
        trust, detail = verify_for("unknown_tool", object(), [])
        self.assertEqual(trust, TRUST_UNVERIFIED)
        self.assertIsNone(detail)
# --- F. Replanning ------------------------------------------------------------


class TestReplanning(unittest.TestCase):
    """F. Replanning: spending-change explanation trajectory."""

    def test_no_followups_for_simple_intent(self) -> None:
        state = AgentState(request="x")
        state.intent = Intent.SPENDING_SUMMARY
        self.assertEqual(decide_followups(state), [])

    def test_no_followups_without_comparison(self) -> None:
        state = AgentState(request="x")
        state.intent = Intent.SPENDING_CHANGE_EXPLANATION
        self.assertEqual(decide_followups(state), [])

    def test_followups_added_on_meaningful_increase(self) -> None:
        from personal_finance_agent.analytics import period_comparison

        transactions = standard_transactions()
        comparison = period_comparison(
            transactions, AUGUST, SEPTEMBER, currency="USD"
        )
        # September (780) > August (400), so there is a meaningful increase.
        self.assertEqual(comparison.change_direction, "increase")

        state = AgentState(request="Why did September spending increase?")
        state.intent = Intent.SPENDING_CHANGE_EXPLANATION
        from personal_finance_agent.runtime.state import Observation

        state.observations.append(
            Observation(
                action_name="period_comparison",
                success=True,
                result=comparison,
            )
        )

        followups = decide_followups(state)
        names = [a.name for a in followups]
        self.assertIn("category_analysis", names)
        self.assertIn("merchant_analysis", names)

    def test_no_followups_on_decrease(self) -> None:
        from personal_finance_agent.analytics import period_comparison

        transactions = standard_transactions()
        comparison = period_comparison(
            transactions, SEPTEMBER, AUGUST, currency="USD"
        )
        self.assertEqual(comparison.change_direction, "decrease")

        state = AgentState(request="x")
        state.intent = Intent.SPENDING_CHANGE_EXPLANATION
        from personal_finance_agent.runtime.state import Observation

        state.observations.append(
            Observation(
                action_name="period_comparison",
                success=True,
                result=comparison,
            )
        )
        self.assertEqual(decide_followups(state), [])
# --- G. Response generation --------------------------------------------------


class TestResponseGeneration(unittest.TestCase):
    """G. Responses use structured evidence; no fabricated numbers."""

    def _make_state(self, intent: Intent, **kwargs) -> AgentState:
        state = AgentState(request="x")
        state.intent = intent
        state.response_status = kwargs.get("status", ResponseStatus.VERIFIED)
        for key, value in kwargs.items():
            if key == "status":
                continue
            setattr(state, key, value)
        return state

    def test_unsupported_response(self) -> None:
        state = self._make_state(Intent.SPENDING_SUMMARY, status=ResponseStatus.UNSUPPORTED)
        response = generate_response(state)
        self.assertIn("can't handle", response.lower())

    def test_ambiguous_response(self) -> None:
        state = self._make_state(Intent.SPENDING_SUMMARY, status=ResponseStatus.AMBIGUOUS)
        response = generate_response(state)
        self.assertIn("ambiguous", response.lower())

    def test_error_response_lists_errors(self) -> None:
        state = self._make_state(
            Intent.SPENDING_SUMMARY,
            status=ResponseStatus.ERROR,
            errors=["boom"],
        )
        response = generate_response(state)
        self.assertIn("boom", response)

    def test_spending_summary_uses_result_total(self) -> None:
        from personal_finance_agent.analytics import spending_summary
        from personal_finance_agent.runtime.state import (
            Observation,
            VerificationRecord,
        )

        transactions = standard_transactions()
        result = spending_summary(transactions, AUGUST, currency="USD")
        state = self._make_state(Intent.SPENDING_SUMMARY, observations=[])
        state.observations.append(
            Observation(action_name="spending_summary", success=True, result=result)
        )
        state.verification_records.append(
            VerificationRecord(
                action_name="spending_summary", status="passed", trust=TRUST_VERIFIED
            )
        )
        response = generate_response(state)
        self.assertIn("400.00", response)
        self.assertIn("USD", response)

    def test_unverified_result_blocked(self) -> None:
        from personal_finance_agent.analytics import spending_summary
        from personal_finance_agent.runtime.state import Observation

        transactions = standard_transactions()
        result = spending_summary(transactions, AUGUST, currency="USD")
        state = self._make_state(Intent.SPENDING_SUMMARY, observations=[])
        state.observations.append(
            Observation(action_name="spending_summary", success=True, result=result)
        )
        # No verification record -> not verified.
        response = generate_response(state)
        self.assertIn("could not be verified", response)
# --- H. End-to-end agent tests -----------------------------------------------


class TestEndToEndAgent(unittest.TestCase):
    """H. End-to-end: full deterministic runtime against synthetic data."""

    def _load_transactions(self) -> tuple[Transaction, ...]:
        from personal_finance_agent.data import load_csv
        from personal_finance_agent.normalization import normalize_records
        from personal_finance_agent.synthetic import SYNTHETIC_CSV_PATH
        from personal_finance_agent.validation import validate_records

        loaded = load_csv(SYNTHETIC_CSV_PATH)
        validated = validate_records(loaded.raw_records)
        return tuple(normalize_records(validated.accepted))

    def test_end_to_end_spending_summary(self) -> None:
        transactions = self._load_transactions()
        state = run("How much did I spend in August 2025?", transactions)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        self.assertIn("USD", state.response)
        self.assertEqual(state.intent, Intent.SPENDING_SUMMARY)
        self.assertTrue(state.verified("spending_summary"))

    def test_end_to_end_unsupported(self) -> None:
        transactions = self._load_transactions()
        state = run("Tell me a joke", transactions)
        self.assertEqual(state.response_status, ResponseStatus.UNSUPPORTED)

    def test_end_to_end_category_analysis(self) -> None:
        transactions = self._load_transactions()
        state = run("Spending by category for September", transactions)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        self.assertEqual(state.intent, Intent.CATEGORY_ANALYSIS)
        self.assertTrue(state.verified("category_analysis"))

    def test_end_to_end_period_comparison(self) -> None:
        transactions = self._load_transactions()
        state = run("Compare August 2025 and September 2025", transactions)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        self.assertEqual(state.intent, Intent.PERIOD_COMPARISON)

    def test_end_to_end_spending_change(self) -> None:
        transactions = self._load_transactions()
        state = run("Why did my spending change in September?", transactions)
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        self.assertEqual(state.intent, Intent.SPENDING_CHANGE_EXPLANATION)
        # The change trajectory should have produced multiple observations.
        self.assertGreaterEqual(len(state.observations), 2)
        # Trajectory is inspectable.
        stages = [entry.stage for entry in state.trajectory]
        self.assertIn(TrajectoryStage.UNDERSTAND, stages)
        self.assertIn(TrajectoryStage.EXECUTE, stages)
        self.assertIn(TrajectoryStage.VERIFY, stages)
        self.assertIn(TrajectoryStage.RESPOND, stages)

    def test_agent_wrapper(self) -> None:
        transactions = self._load_transactions()
        agent = Agent(transactions)
        state = agent.execute("How much did I spend in September?")
        self.assertEqual(state.response_status, ResponseStatus.VERIFIED)
        self.assertIn("USD", state.response)
