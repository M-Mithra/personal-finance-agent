"""Command line entry point for the deterministic evaluation baseline."""
from __future__ import annotations

import argparse
from pathlib import Path

from .models import ExecutionMode
from .runner import EvaluationRunner, serialize_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Personal Finance Agent evaluation")
    parser.add_argument("--eval-dir", default="eval")
    parser.add_argument("--suite", choices=("core", "robustness"))
    parser.add_argument("--mode", choices=("deterministic", "llm"), default="deterministic")
    parser.add_argument("--output-dir", default="eval/results")
    args = parser.parse_args()
    mode = ExecutionMode(args.mode)
    report = EvaluationRunner(args.eval_dir).run(args.suite, mode)
    output = Path(args.output_dir) / f"{report.run_id}.json"
    serialize_report(report, output)
    print(f"run_id={report.run_id} cases={len(report.cases)} output={output}")
    print(report.aggregate())


if __name__ == "__main__":
    main()
