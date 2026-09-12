"""Evaluation result models for the Personal Finance Agent evaluation runner.

Pure data structures; do not import from production agent implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DimensionStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "N/A"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ExecutionMode(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class CaseStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ERROR = "ERROR"


@dataclass(slots=True)
class DimensionScore:
    name: str
    status: DimensionStatus
    score: float | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "score": self.score, "reason": self.reason}


@dataclass(slots=True)
class ReviewItem:
    case_id: str
    dimension: str
    reason: str
    response: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"case_id": self.case_id, "dimension": self.dimension,
                "reason": self.reason, "response": self.response}


@dataclass(slots=True)
class CaseResult:
    case_id: str
    suite: str
    category: str
    execution_mode: ExecutionMode
    expected_intent: str
    actual_intent: str
    termination_reason: str | None
    response: str
    status: CaseStatus
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    failed_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trajectory_summary: list[dict[str, str]] = field(default_factory=list)
    tool_calls: list[str] = field(default_factory=list)
    execution_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id, "suite": self.suite, "category": self.category,
            "execution_mode": self.execution_mode.value, "expected_intent": self.expected_intent,
            "actual_intent": self.actual_intent, "termination_reason": self.termination_reason,
            "response": self.response, "status": self.status.value,
            "dimensions": {key: value.to_dict() for key, value in self.dimensions.items()},
            "failed_checks": self.failed_checks, "warnings": self.warnings,
            "trajectory_summary": self.trajectory_summary, "tool_calls": self.tool_calls,
            "execution_metadata": self.execution_metadata,
        }


@dataclass(slots=True)
class EvaluationReport:
    run_id: str
    execution_mode: ExecutionMode
    cases: list[CaseResult]
    reviews: list[ReviewItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def aggregate(self) -> dict[str, Any]:
        def summary(items: list[CaseResult]) -> dict[str, Any]:
            return {"cases_executed": len(items),
                    "cases_passed": sum(item.status is CaseStatus.PASS for item in items),
                    "cases_failed": sum(item.status is CaseStatus.FAIL for item in items),
                    "cases_needing_review": sum(item.status is CaseStatus.NEEDS_REVIEW for item in items)}
        groups: dict[str, list[CaseResult]] = {"overall": self.cases}
        groups.update({suite: [item for item in self.cases if item.suite == suite]
                       for suite in {item.suite for item in self.cases}})
        categories = {item.category for item in self.cases}
        groups.update({
            f"category_{'edge_case' if category == 'robustness' else category}": [
                item for item in self.cases
                if item.category == category or (
                    category == 'edge_case' and item.category == 'robustness'
                )
            ]
            for category in categories
            if category != 'robustness'
        })
        return {name: summary(items) for name, items in groups.items()}

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "execution_mode": self.execution_mode.value,
                "metadata": self.metadata, "aggregate": self.aggregate(),
                "cases": [case.to_dict() for case in self.cases],
                "human_review": [review.to_dict() for review in self.reviews]}
