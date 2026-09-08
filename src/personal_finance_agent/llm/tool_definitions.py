"""Provider-neutral tool definitions shown to the LLM.

A tool definition is **metadata only**: it describes a tool's name, purpose,
and input arguments so a model can select it correctly. It deliberately does
not duplicate the analytical implementation; execution still happens through
``runtime.tools.execute_tool`` after the runtime validates a proposed call.

The definitions correspond 1:1 to the five registered analytical tools in
``runtime.tools.TOOLS``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "DEFAULT_TOOL_DEFINITIONS",
    "ToolArgumentSchema",
    "ToolDefinition",
    "tool_definition_for",
]


@dataclass(frozen=True, slots=True)
class ToolArgumentSchema:
    """Input contract for one tool argument, expressed for model selection."""

    name: str
    type: str
    required: bool
    description: str = ""


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Metadata describing one available tool to a model."""

    name: str
    description: str
    arguments: tuple[ToolArgumentSchema, ...] = field(default_factory=tuple)


def _period_arg(required: bool = True) -> ToolArgumentSchema:
    return ToolArgumentSchema(
        name="period",
        type="Period",
        required=required,
        description=(
            "an inclusive calendar period; a month reference such as "
            "'2025-08' or the month label of the analysis scope"
        ),
    )


DEFAULT_TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="spending_summary",
        description=(
            "Calculate total spending (expenses only) for a single period, "
            "with transaction count and included-transaction evidence."
        ),
        arguments=(_period_arg(),),
    ),
    ToolDefinition(
        name="category_analysis",
        description=(
            "Group spending by category for a single period and return "
            "per-category totals ordered by total descending."
        ),
        arguments=(_period_arg(),),
    ),
    ToolDefinition(
        name="period_comparison",
        description=(
            "Compare spending between two periods and return both totals, "
            "the absolute difference, the percentage difference, and the "
            "change direction."
        ),
        arguments=(
            ToolArgumentSchema(
                name="period_a",
                type="Period",
                required=True,
                description="the earlier period for the comparison",
            ),
            ToolArgumentSchema(
                name="period_b",
                type="Period",
                required=True,
                description="the later period for the comparison",
            ),
        ),
    ),
    ToolDefinition(
        name="merchant_analysis",
        description=(
            "Identify merchants contributing the most to spending in a "
            "single period, ordered by total descending."
        ),
        arguments=(_period_arg(),),
    ),
    ToolDefinition(
        name="noteworthy_transactions",
        description=(
            "Identify the largest expenses in a single period using a "
            "deterministic ranking rule (top N by amount)."
        ),
        arguments=(
            _period_arg(),
            ToolArgumentSchema(
                name="limit",
                type="int",
                required=False,
                description="maximum number of expenses to return (default 5)",
            ),
        ),
    ),
)


def tool_definition_for(name: str) -> ToolDefinition | None:
    """Return the tool definition for ``name``, or ``None`` if unknown."""
    for definition in DEFAULT_TOOL_DEFINITIONS:
        if definition.name == name:
            return definition
    return None