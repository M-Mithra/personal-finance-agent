"""Command line entry point for the evaluation runner."""
from __future__ import annotations

import argparse
from pathlib import Path

from .models import ExecutionMode
from .runner import EvaluationRunner, serialize_report, LLMLoopConfig
from personal_finance_agent.llm.ollama import OllamaLLMClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Personal Finance Agent evaluation")
    parser.add_argument("--eval-dir", default="eval")
    parser.add_argument("--suite", choices=("core", "robustness"))
    parser.add_argument("--mode", choices=("deterministic", "llm"), default="deterministic")
    parser.add_argument("--output-dir", default="eval/results")
    parser.add_argument("--model", default="qwen3:1.7b", help="Ollama model identifier (used when --mode=llm)")
    parser.add_argument("--base-url", default=None, help="Ollama base URL (default: http://localhost:11434)")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout in seconds")
    args = parser.parse_args()
    mode = ExecutionMode(args.mode)

    if mode is ExecutionMode.LLM:
        base_url = args.base_url or "http://localhost:11434"
        llm_client = OllamaLLMClient(
            model=args.model,
            base_url=base_url,
            timeout=args.timeout,
        )
        llm_config = LLMLoopConfig()
        runner = EvaluationRunner(args.eval_dir, llm_client=llm_client, llm_config=llm_config)
    else:
        runner = EvaluationRunner(args.eval_dir)

    report = runner.run(args.suite, mode)
    output = Path(args.output_dir) / f"{report.run_id}.json"
    serialize_report(report, output)
    print(f"run_id={report.run_id} cases={len(report.cases)} output={output}")
    print(report.aggregate())


if __name__ == "__main__":
    main()
