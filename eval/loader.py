"""Evaluation data loading and validation."""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


# Valid intents from the actual implementation
VALID_INTENTS = frozenset({
    "spending_summary",
    "category_analysis",
    "period_comparison",
    "merchant_analysis",
    "noteworthy_transactions",
    "spending_change_explanation",
    "unsupported",
    "ambiguous",
})

VALID_TOOLS = frozenset({
    "spending_summary",
    "category_analysis",
    "period_comparison",
    "merchant_analysis",
    "noteworthy_transactions",
})

VALID_CATEGORIES = frozenset({
    "basic_analytical",
    "multi_step",
    "ambiguous",
    "safety",
    "grounding",
    "edge_case",
    "robustness",
})

VALID_SUITES = frozenset({"core", "robustness"})
REQUIRED_GROUND_TRUTH_PERIODS = frozenset({"august_2025", "september_2025"})


class EvaluationSpecValidationError(Exception):
    """Raised when the evaluation specification has validation errors."""
    pass


def load_json(path: Path) -> dict:
    """Load and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise EvaluationSpecValidationError(f"{path} must contain a JSON object")
    return value


def validate_case(case: dict, index: int) -> list[str]:
    """Validate a single evaluation case. Returns list of errors."""
    errors = []
    if not isinstance(case, dict):
        return [f"Case[{index}] must be an object"]
    
    # Required fields
    required_fields = [
        "case_id", "category", "dataset", "user_prompt",
        "expected_intent", "fact_establishing_tools",
        "explanation_supporting_tools", "acceptable_argument_constraints",
        "expected_deterministic_facts", "forbidden_claims",
        "expected_behavior", "safety_relevant",
        "human_review_focus", "notes",
    ]
    
    for field in required_fields:
        if field not in case:
            errors.append(f"Case[{index}] ({case.get('case_id', 'UNKNOWN')}): missing required field '{field}'")
    
    # case_id format
    case_id = case.get("case_id", "")
    if not case_id.startswith("EVAL-"):
        errors.append(f"Case[{index}]: case_id must start with 'EVAL-', got '{case_id}'")
    
    # Check for duplicates (will be caught at collection level)
    
    # category
    category = case.get("category", "")
    if category not in VALID_CATEGORIES:
        errors.append(f"Case[{index}] ({case_id}): invalid category '{category}'")
    
    # dataset
    dataset = case.get("dataset", "")
    if not dataset.startswith("dataset_"):
        errors.append(f"Case[{index}] ({case_id}): invalid dataset reference '{dataset}'")
    
    # expected_intent
    intent = case.get("expected_intent", "")
    if intent not in VALID_INTENTS:
        errors.append(f"Case[{index}] ({case_id}): invalid expected_intent '{intent}'")
    
    # fact_establishing_tools
    fet = case.get("fact_establishing_tools", [])
    if not isinstance(fet, list):
        errors.append(f"Case[{index}] ({case_id}): fact_establishing_tools must be a list")
    else:
        for tool in fet:
            if tool not in VALID_TOOLS:
                errors.append(f"Case[{index}] ({case_id}): invalid fact_establishing_tool '{tool}'")
    
    # explanation_supporting_tools
    est = case.get("explanation_supporting_tools", [])
    if not isinstance(est, list):
        errors.append(f"Case[{index}] ({case_id}): explanation_supporting_tools must be a list")
    else:
        for tool in est:
            if tool not in VALID_TOOLS:
                errors.append(f"Case[{index}] ({case_id}): invalid explanation_supporting_tool '{tool}'")

    if not isinstance(case.get("acceptable_argument_constraints"), dict):
        errors.append(f"Case[{index}] ({case_id}): acceptable_argument_constraints must be an object")
    
    # safety_relevant should be boolean
    if not isinstance(case.get("safety_relevant"), bool):
        errors.append(f"Case[{index}] ({case_id}): safety_relevant must be boolean")
    
    return errors


def validate_suites(cases_data: dict) -> list[str]:
    """Validate the entire suites structure. Returns list of errors."""
    errors = []
    
    # Check for suite field on each case
    seen_ids = set()
    cases = cases_data.get("cases")
    if not isinstance(cases, list):
        return ["cases must be a list"]
    for i, case in enumerate(cases):
        case_id = case.get("case_id", f"UNKNOWN[{i}]")
        
        if case_id in seen_ids:
            errors.append(f"Duplicate case_id: {case_id}")
        seen_ids.add(case_id)
        
        errors.extend(validate_case(case, i))
        if isinstance(case, dict) and case.get("suite") not in VALID_SUITES:
            errors.append(f"Case[{i}] ({case_id}): unknown suite '{case.get('suite')}'")
    
    return errors


def _require_fields(value: object, fields: tuple[str, ...], path: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{path} must be an object"]
    return [f"{path} missing required field '{field}'" for field in fields if field not in value]


def _is_numeric(value: object) -> bool:
    try:
        Decimal(str(value).replace(" USD", "").replace("%", ""))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return True


def validate_ground_truth(ground_truth: dict) -> list[str]:
    """Validate the ground-truth structures consumed by the runner."""
    errors: list[str] = []
    errors.extend(_require_fields(ground_truth, ("metadata", "dataset_summary", "periods", "period_comparison"), "ground_truth"))
    summary = ground_truth.get("dataset_summary")
    errors.extend(_require_fields(summary, ("total_records", "accepted", "rejected", "periods", "currency"), "ground_truth.dataset_summary"))
    if isinstance(summary, dict):
        for field in ("total_records", "accepted", "rejected"):
            if not isinstance(summary.get(field), int):
                errors.append(f"ground_truth.dataset_summary.{field} must be an integer")
        if not isinstance(summary.get("periods"), list) or not all(isinstance(item, str) for item in summary.get("periods", [])):
            errors.append("ground_truth.dataset_summary.periods must be a list of strings")
    periods = ground_truth.get("periods")
    if not isinstance(periods, dict):
        return errors + ["ground_truth.periods must be an object"]
    missing_periods = REQUIRED_GROUND_TRUTH_PERIODS - set(periods)
    errors.extend(f"ground_truth.periods missing '{period}'" for period in sorted(missing_periods))
    for period_id, period in periods.items():
        path = f"ground_truth.periods.{period_id}"
        errors.extend(_require_fields(period, ("label", "start", "end", "period_id", "spending_summary"), path))
        if not isinstance(period, dict):
            continue
        summary = period.get("spending_summary")
        errors.extend(_require_fields(summary, ("total", "transaction_count", "status"), f"{path}.spending_summary"))
        if isinstance(summary, dict):
            if not _is_numeric(summary.get("total")):
                errors.append(f"{path}.spending_summary.total must be numeric")
            if not isinstance(summary.get("transaction_count"), int):
                errors.append(f"{path}.spending_summary.transaction_count must be an integer")
        category = period.get("category_analysis")
        if category is not None:
            errors.extend(_require_fields(category, ("total_spending", "category_count", "categories"), f"{path}.category_analysis"))
            if isinstance(category, dict):
                if not _is_numeric(category.get("total_spending")):
                    errors.append(f"{path}.category_analysis.total_spending must be numeric")
                if not isinstance(category.get("categories"), list):
                    errors.append(f"{path}.category_analysis.categories must be a list")
                else:
                    for index, item in enumerate(category["categories"]):
                        item_path = f"{path}.category_analysis.categories[{index}]"
                        errors.extend(_require_fields(item, ("category", "total", "count", "ids"), item_path))
                        if isinstance(item, dict) and not _is_numeric(item.get("total")):
                            errors.append(f"{item_path}.total must be numeric")
        merchant = period.get("merchant_analysis")
        if merchant is not None:
            errors.extend(_require_fields(merchant, ("total_spending", "merchant_count", "top_merchants"), f"{path}.merchant_analysis"))
            if isinstance(merchant, dict):
                if not _is_numeric(merchant.get("total_spending")):
                    errors.append(f"{path}.merchant_analysis.total_spending must be numeric")
                if not isinstance(merchant.get("top_merchants"), list):
                    errors.append(f"{path}.merchant_analysis.top_merchants must be a list")
                else:
                    for index, item in enumerate(merchant["top_merchants"]):
                        item_path = f"{path}.merchant_analysis.top_merchants[{index}]"
                        errors.extend(_require_fields(item, ("merchant", "total", "count", "ids"), item_path))
                        if isinstance(item, dict) and not _is_numeric(item.get("total")):
                            errors.append(f"{item_path}.total must be numeric")
        noteworthy = period.get("noteworthy_transactions")
        if noteworthy is not None:
            errors.extend(_require_fields(noteworthy, ("limit", "largest"), f"{path}.noteworthy_transactions"))
            if isinstance(noteworthy, dict):
                if not isinstance(noteworthy.get("largest"), list):
                    errors.append(f"{path}.noteworthy_transactions.largest must be a list")
                else:
                    for index, item in enumerate(noteworthy["largest"]):
                        item_path = f"{path}.noteworthy_transactions.largest[{index}]"
                        errors.extend(_require_fields(item, ("rank", "id", "date", "amount", "merchant"), item_path))
                        if isinstance(item, dict):
                            if not isinstance(item.get("rank"), int):
                                errors.append(f"{item_path}.rank must be an integer")
                            if not _is_numeric(item.get("amount")):
                                errors.append(f"{item_path}.amount must be numeric")
    comparison = ground_truth.get("period_comparison")
    errors.extend(_require_fields(comparison, ("aug_vs_sep",), "ground_truth.period_comparison"))
    if isinstance(comparison, dict) and isinstance(comparison.get("aug_vs_sep"), dict):
        comparison_path = "ground_truth.period_comparison.aug_vs_sep"
        values = comparison["aug_vs_sep"]
        errors.extend(_require_fields(values, ("period_a", "period_b", "total_a", "total_b", "absolute_difference", "change_direction"), comparison_path))
        for field in ("total_a", "total_b", "absolute_difference", "percentage_difference"):
            if field in values and values[field] is not None and not _is_numeric(values[field]):
                errors.append(f"{comparison_path}.{field} must be numeric")
    return errors


def load_eval_spec(eval_dir: str = "eval") -> dict:
    """Load and validate the complete evaluation specification.
    
    Returns a dict with:
    - cases: list of all cases from cases.json
    - ground_truth: the ground truth data
    - datasets: dataset definitions
    - errors: validation errors (empty if valid)
    """
    base = Path(eval_dir)
    
    if not base.is_dir():
        raise FileNotFoundError(f"Eval directory not found: {eval_dir}")
    
    # Load files
    core = load_json(base / "cases_core.json")
    robust = load_json(base / "cases_robust.json")
    cases_data = load_json(base / "cases.json")
    ground_truth = load_json(base / "ground_truth.json")
    datasets = load_json(base / "datasets.json")
    
    # Validate
    errors = validate_suites(cases_data)
    datasets_map = datasets.get("datasets")
    if not isinstance(datasets_map, dict):
        errors.append("datasets.datasets must be an object")
        datasets_map = {}
    catalog_ids = {case.get("case_id") for case in cases_data.get("cases", [])
                   if isinstance(case, dict)}
    for case in cases_data.get("cases", []):
        if isinstance(case, dict) and case.get("dataset") not in datasets_map:
            errors.append(f"{case.get('case_id', 'UNKNOWN')}: unknown dataset '{case.get('dataset')}'")
    for suite_name, suite_data in (("core", core), ("robustness", robust)):
        errors.extend(f"{suite_name}: {error}" for error in validate_suites(suite_data))
        for case in suite_data.get("cases", []):
            if isinstance(case, dict) and case.get("case_id") not in catalog_ids:
                errors.append(f"{suite_name}: case {case.get('case_id')} missing from cases.json")
    if errors:
        raise EvaluationSpecValidationError("Invalid evaluation specification:\n" + "\n".join(errors))
    ground_truth_errors = validate_ground_truth(ground_truth)
    if ground_truth_errors:
        raise EvaluationSpecValidationError("Invalid ground truth:\n" + "\n".join(ground_truth_errors))
    
    return {
        "cases": cases_data.get("cases", []),
        "ground_truth": ground_truth,
        "datasets": datasets_map,
        "errors": [],
        "metadata": cases_data.get("metadata", {}),
        "suites": cases_data.get("suites", {}),
    }


def load_case_suite(eval_dir: str, suite: str) -> list[dict]:
    """Load a specific suite (core or robustness)."""
    base = Path(eval_dir)
    suite_filename_map = {
        "core": "cases_core.json",
        "robustness": "cases_robust.json",
    }
    filename = suite_filename_map.get(suite, f"cases_{suite}.json")
    path = base / filename
    
    if not path.exists():
        raise FileNotFoundError(f"Suite file not found: {filename}")
    
    data = load_json(path)
    return data.get("cases", [])
