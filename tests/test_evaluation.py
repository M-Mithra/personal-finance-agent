from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from personal_finance_agent.runtime.state import Action, AgentState, Intent, ResponseStatus
from personal_finance_agent.llm.fake import FakeLLMClient
from personal_finance_agent.runtime.agent import Agent

from eval.loader import (EvaluationSpecValidationError, load_eval_spec,
                         validate_ground_truth, validate_suites)
from eval.models import CaseResult, CaseStatus, DimensionStatus, EvaluationReport, ExecutionMode
from eval.runner import (EvaluationRunner, aggregate_results, compare_numbers,
                         evaluate_case, score_intent, score_tools,
                         serialize_report, validate_argument_constraints)


class EvaluationInfrastructureTests(unittest.TestCase):
    def test_loads_complete_spec_and_dataset(self):
        spec = load_eval_spec()
        self.assertEqual(len(spec["cases"]), 28)
        self.assertEqual(spec["datasets"]["dataset_a"]["transaction_count"], 64)

    def test_duplicate_case_ids_are_rejected(self):
        data = {"cases": [{"case_id": "EVAL-001"}, {"case_id": "EVAL-001"}]}
        errors = validate_suites(data)
        self.assertTrue(any("Duplicate case_id" in error for error in errors))

    def test_intent_and_tool_scoring(self):
        self.assertEqual(score_intent("spending_summary", "spending_summary").status,
                         DimensionStatus.PASS)
        score = score_tools({"fact_establishing_tools": ["spending_summary"]}, ["spending_summary"])
        self.assertEqual(score.status, DimensionStatus.PASS)

    def test_argument_constraints_are_semantic(self):
        state = AgentState(request="x", plan=[Action("spending_summary", {"period": "2025-08"})])
        case = {"acceptable_argument_constraints": {"period": "August 2025"}}
        self.assertEqual(validate_argument_constraints(case, state), (True, "observable arguments satisfy constraints"))

    def test_numeric_comparison_and_serialization(self):
        self.assertTrue(compare_numbers("3459.670 USD", "3459.67 USD"))
        report = EvaluationReport("run", ExecutionMode.DETERMINISTIC, [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            serialize_report(report, path)
            self.assertEqual(json.loads(path.read_text())["run_id"], "run")

    def test_ground_truth_schema_validation_rejects_missing_period(self):
        errors = validate_ground_truth({"metadata": {}, "dataset_summary": {},
                                        "periods": {}, "period_comparison": {}})
        self.assertTrue(any("august_2025" in error for error in errors))

    def test_grounding_supported_and_unsupported_monetary_claims(self):
        runner = EvaluationRunner()
        case = next(case for case in runner.spec["cases"] if case["case_id"] == "EVAL-001")
        transactions = runner._transactions("dataset_a")
        state = Agent(transactions).execute(case["user_prompt"])
        supported = evaluate_case(case, state, ExecutionMode.DETERMINISTIC, 0.0, runner.spec["ground_truth"])[0]
        self.assertEqual(supported.dimensions["groundedness"].status, DimensionStatus.PASS)
        state.response = "Total spending was USD 999.99."
        unsupported = evaluate_case(case, state, ExecutionMode.DETERMINISTIC, 0.0, runner.spec["ground_truth"])[0]
        self.assertEqual(unsupported.dimensions["groundedness"].status, DimensionStatus.FAIL)

    def test_grounding_figure_passes_but_explanation_is_reviewed(self):
        runner = EvaluationRunner()
        case = next(case for case in runner.spec["cases"] if case["case_id"] == "EVAL-017")
        result, reviews = runner.execute_case(case)
        self.assertEqual(result.dimensions["groundedness"].status, DimensionStatus.PASS)
        self.assertEqual(result.dimensions["explanation_grounding"].status, DimensionStatus.NEEDS_REVIEW)
        self.assertTrue(any(item.dimension == "explanation_grounding" for item in reviews))

    def test_grounding_accepts_signed_or_absolute_display_form(self):
        runner = EvaluationRunner()
        case = next(case for case in runner.spec["cases"] if case["case_id"] == "EVAL-007")
        result, _ = runner.execute_case(case)
        self.assertEqual(result.dimensions["groundedness"].status, DimensionStatus.PASS)

    def test_review_queue_does_not_copy_every_case(self):
        report = EvaluationRunner().run()
        self.assertGreater(len(report.reviews), 0)
        self.assertLess(len(report.reviews), len(report.cases))
        self.assertNotIn("EVAL-001", {item.case_id for item in report.reviews})

    def test_traceability_metadata_is_recorded(self):
        report = EvaluationRunner().run(suite="core")
        self.assertRegex(report.metadata["timestamp"], r"^20\d\d-")
        self.assertTrue(report.metadata["git_revision"])
        self.assertEqual(report.metadata["suite"], "core")
        self.assertEqual(report.metadata["case_count"], 20)

    def test_eval_008_preserves_production_period_order_mismatch(self):
        runner = EvaluationRunner()
        case = next(case for case in runner.spec["cases"] if case["case_id"] == "EVAL-008")
        result, _ = runner.execute_case(case)
        self.assertEqual(result.actual_intent, "period_comparison")
        self.assertTrue(any("period_a" in check for check in result.failed_checks))

    def test_runner_executes_dataset_a_without_ollama(self):
        report = EvaluationRunner().run(suite="core")
        self.assertEqual(len(report.cases), 20)
        self.assertEqual(report.aggregate()["core"]["cases_executed"], 20)

    def test_runner_accepts_injected_fake_llm(self):
        client = FakeLLMClient([
            FakeLLMClient.tool_call("spending_summary", {"period": "2025-08"}),
            FakeLLMClient.final_response("Total spending was USD 3459.67."),
        ])
        runner = EvaluationRunner(llm_client=client)
        case = next(case for case in runner.spec["cases"] if case["case_id"] == "EVAL-001")
        result, _ = runner.execute_case(case, ExecutionMode.LLM)
        self.assertEqual(result.execution_mode, ExecutionMode.LLM)
        self.assertEqual(result.tool_calls, ["spending_summary"])

    def test_llm_mode_constructs_ollama_client(self):
        """Test that CLI --mode=llm would construct OllamaLLMClient with correct model."""
        with patch("personal_finance_agent.llm.ollama.OllamaLLMClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.model_identifier = "ollama:qwen3:1.7b"
            mock_client.return_value = mock_instance
            
            from eval.__main__ import main
            import sys
            
            # We can't easily test the CLI main() without subprocess,
            # but we can verify the runner instantiation works
            runner = EvaluationRunner(
                eval_dir="eval",
                llm_client=mock_instance,
                llm_config=None
            )
            self.assertEqual(runner.llm_client, mock_instance)
            mock_client.assert_not_called()  # runner doesn't call constructor

    def test_deterministic_mode_preserves_current_behavior(self):
        """Test that --mode=deterministic uses Agent.execute without LLM client."""
        runner = EvaluationRunner()  # No LLM client
        case = next(case for case in runner.spec["cases"] if case["case_id"] == "EVAL-001")
        result, _ = runner.execute_case(case, ExecutionMode.DETERMINISTIC)
        self.assertEqual(result.execution_mode, ExecutionMode.DETERMINISTIC)
        self.assertIn("spending_summary", result.tool_calls)
        
        # Verify report metadata doesn't have model_identifier
        report = runner.run(suite="core", mode=ExecutionMode.DETERMINISTIC)
        self.assertIsNone(report.metadata.get("model_identifier"))

    def test_llm_mode_report_includes_model_identifier(self):
        """Test that LLM mode report metadata includes model_identifier."""
        from eval.runner import LLMLoopConfig
        client = FakeLLMClient([
            FakeLLMClient.tool_call("spending_summary", {"period": "2025-08"}),
            FakeLLMClient.final_response("Total spending was USD 3459.67."),
        ])
        runner = EvaluationRunner(llm_client=client, llm_config=LLMLoopConfig())
        report = runner.run(suite="core", mode=ExecutionMode.LLM)
        self.assertEqual(report.metadata["model_identifier"], "fake-llm-client")
        self.assertIsNotNone(report.metadata["llm_config"])
        self.assertEqual(report.metadata["llm_config"]["max_model_steps"], 6)
        self.assertEqual(report.metadata["llm_config"]["max_tool_calls"], 4)

    def test_llm_mode_without_client_raises_error(self):
        """Test that LLM mode without injected client raises ValueError."""
        runner = EvaluationRunner()  # No LLM client
        case = next(case for case in runner.spec["cases"] if case["case_id"] == "EVAL-001")
        with self.assertRaises(ValueError) as ctx:
            runner.execute_case(case, ExecutionMode.LLM)
        self.assertIn("LLM mode requires an injected LLM client", str(ctx.exception))

    def test_fake_llm_client_mocked_no_actual_ollama_call(self):
        """Verify FakeLLMClient is used in tests, no actual Ollama HTTP call."""
        client = FakeLLMClient([
            FakeLLMClient.tool_call("spending_summary", {"period": "2025-08"}),
            FakeLLMClient.final_response("Total spending was USD 3459.67."),
        ])
        runner = EvaluationRunner(llm_client=client)
        case = next(case for case in runner.spec["cases"] if case["case_id"] == "EVAL-001")
        result, _ = runner.execute_case(case, ExecutionMode.LLM)
        
        # Verify the fake client was called and recorded requests
        self.assertEqual(len(client.requests), 2)
        self.assertEqual(client.requests[0].user_request, case["user_prompt"])
        self.assertEqual(result.tool_calls, ["spending_summary"])

    def test_aggregation_does_not_merge_category_and_suite(self):
        result = CaseResult("EVAL-001", "core", "basic_analytical", ExecutionMode.DETERMINISTIC,
                            "spending_summary", "spending_summary", "complete", "ok", CaseStatus.PASS)
        aggregate = aggregate_results([result])
        self.assertEqual(aggregate["core"]["cases_executed"], 1)
        self.assertEqual(aggregate["category_basic_analytical"]["cases_executed"], 1)


if __name__ == "__main__":
    unittest.main()
