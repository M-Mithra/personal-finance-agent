# 1. Implementation Overview

This document explains how the approved requirements and designs will be translated into software for the Personal Finance Agent. It follows the problem and objectives in `docs/01_problem_and_objectives.md`, the requirements in `docs/02_requirements.md`, the system organization in `docs/03_system_design.md`, the agent behavior in `docs/04_agent_design.md`, and the logical data model in `docs/05_data_design.md`.

Design documents define responsibilities, boundaries, behavior, and logical data. This document makes the first implementation choices needed to build and test a working vertical slice. It does not claim to define the final production system.

The implementation philosophy is:

```text
Start simple
  -> Build a working vertical slice
  -> Test it
  -> Evaluate it
  -> Add complexity only when justified
```

The MVP should demonstrate:

```text
User Request
  -> Understand
  -> Decide / Plan
  -> Analytical Action
  -> Observe
  -> Validate
  -> Verify
  -> Grounded Response
```

Implementation choices are traceable to the earlier requirements and design decisions. Choices that are not yet justified, such as a specific model provider, database, hosted deployment, or persistent memory mechanism, remain deferred.

# 2. Implementation Principles

## 2.1 Simplicity

Use the smallest implementation that demonstrates the required behavior. Avoid infrastructure, abstractions, and dependencies that do not support a current MVP requirement.

## 2.2 Modularity

Keep data handling, validation, normalization, analytics, agent state, action dispatch, verification, response generation, and observability as understandable software boundaries. A logical boundary does not require a separate package or service.

## 2.3 Separation of concerns

The agent should decide and interpret; analytical capabilities should calculate; verification should check. Request handling and data loading should not contain hidden financial analysis or response-generation logic.

## 2.4 Deterministic computation where appropriate

Use conventional Python computation for arithmetic, filtering, grouping, period comparison, and numerical verification. The agent must not become the source of truth for calculations that can be performed deterministically.

## 2.5 Agent reasoning where useful

Use reasoning for request understanding, intent interpretation, planning, ambiguity handling, contextual follow-up, and grounded response generation where it adds value. The exact LLM or reasoning provider is not selected yet.

## 2.6 Explicit state

Represent the current request, interpreted intent, plan, actions, observations, errors, verification status, evidence, and response status explicitly enough to inspect an execution.

## 2.7 Verification

Treat verification as an independent implementation responsibility. A response should not present an important result as reliable merely because an analytical action returned a value.

## 2.8 Testability

Prefer small functions and modules with clear inputs and outputs. Data validation, normalization, analytics, action dispatch, state transitions, and verification should be testable without requiring a live model or external service.

## 2.9 Observability

Record enough information to inspect an agent trajectory, selected action, result status, verification outcome, and failures. Keep the initial implementation simpler than a distributed tracing system.

## 2.10 Reproducibility

Use deterministic sample data and explicit analytical parameters for development and tests. Preserve the source/canonical relationship and avoid hidden global state.

## 2.11 Extensibility

Use narrow logical interfaces so a later data source, model, storage mechanism, or analytical capability can be added without rewriting the core domain behavior.

## 2.12 Minimal dependencies

Prefer Python standard-library facilities for the initial data model, file loading, state, logging, and tests. Add a dependency only when it removes a concrete problem that the standard library cannot address adequately.

## 2.13 Incremental development

Implement one working vertical slice at a time. Each slice should produce behavior that can be tested and evaluated before the next layer is added.

# 3. Initial Technology Stack

The repository already establishes the following environment:

| Technology | Purpose | Why Needed | MVP? |
|---|---|---|---|
| Python 3.12+ | Implementation language | The repository requires Python `>=3.12`; it supports the domain model, type annotations, deterministic analytics, and agent state without imposing an application framework. | Yes |
| `uv` | Python environment and dependency management | It is the existing project workflow and provides a reproducible way to manage the environment as dependencies are introduced. | Yes |
| Git | Version control | The project requires traceable source and documentation changes. | Yes |
| VS Code | Development environment | It is the current project editor and supports the existing Python workflow. | Yes, as the development environment |
| macOS | Local development environment | It is the current development platform, not an application runtime requirement. | Yes for local development |

## 3.1 MVP standard-library choices

The initial implementation can use the Python standard library for the following concerns:

| Technology | Purpose | Why Needed | MVP? |
|---|---|---|---|
| `dataclasses` and `typing` | Canonical transaction, result, and execution-state representations | They provide explicit, readable in-memory structures without a schema framework. | Yes |
| `csv` and `json` | Initial local/sample transaction loading and structured result support | They are sufficient for a small, controlled MVP input boundary; the final format remains subject to data-design decisions. | Yes, for initial local data handling |
| `datetime` and `decimal` | Date/period handling and monetary arithmetic | Dates require explicit boundaries, and decimal arithmetic avoids inappropriate binary floating-point behavior for monetary values. | Yes |
| `logging` | Simple execution and error observability | It supports inspectable local execution without distributed tracing infrastructure. | Yes |
| `unittest` | Unit and integration tests | It is included with Python and supports the required test levels without adding a dependency. | Yes |
| `argparse` or a direct Python entry point | Initial local invocation if an interface is needed for the vertical slice | It is sufficient for a small local prototype; a final CLI, web, or other interface remains TBD. | Provisional |

## 3.2 Additional dependencies

No additional runtime dependency is selected at this stage. A data-processing library, LLM client, CLI library, configuration package, structured logging package, or other framework may be added later only when an evaluated requirement justifies it.

An LLM API or provider is not selected. The provider-neutral LLM abstraction (`llm/`) is implemented with the standard library only: it defines the interface, structured response types, error vocabulary, tool definitions, and a deterministic fake client. No SDK, credentials, or provider configuration are introduced.

# 4. Project Structure

The initial repository should evolve toward the following structure without requiring all future directories immediately:

```text
personal-finance-agent/
├── README.md
├── pyproject.toml
├── uv.lock                         # Generated when dependencies are managed by uv
├── .gitignore
├── main.py                         # Temporary or compatibility entry point during migration
├── docs/
│   ├── 01_problem_and_objectives.md
│   ├── 02_requirements.md
│   ├── 03_system_design.md
│   ├── 04_agent_design.md
│   ├── 05_data_design.md
│   ├── 06_implementation.md
│   └── 07_testing_and_evaluation.md
├── src/
│   └── personal_finance_agent/
│       ├── __init__.py
│       ├── models.py
│       ├── data.py
│       ├── validation.py
│       ├── normalization.py
│       ├── synthetic.py
│       ├── analytics.py
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── types.py
│       │   ├── tool_definitions.py
│       │   ├── errors.py
│       │   └── fake.py
│       ├── tools.py
│       ├── agent.py
│       ├── verification.py
│       ├── responses.py
│       ├── config.py
│       └── observability.py
├── tests/
│   ├── test_data.py
│   ├── test_validation.py
│   ├── test_normalization.py
│   ├── test_analytics.py
│   ├── test_llm.py
│   ├── test_tools.py
│   ├── test_agent.py
│   └── test_verification.py
└── data/
    └── sample/
        └── transactions.csv
```

## 4.1 Structure rationale

- `src/personal_finance_agent/models.py` contains canonical transaction, analytical-result, evidence, and execution-state representations.
- `data.py` loads source records and exposes a controlled data-access boundary.
- `validation.py` performs structural, semantic, and analysis-specific validation.
- `normalization.py` maps source records to canonical semantics while preserving source values.
- `analytics.py` contains deterministic transaction calculations and analysis operations.
- `tools.py` exposes analytical capabilities through small, explicit action boundaries.
- `agent.py` contains the single-agent runtime and state transitions.
- `verification.py` checks tool results and candidate responses against evidence.
- `responses.py` turns verified results or bounded failures into user-facing responses.
- `config.py` contains non-secret runtime configuration and feature options.
- `observability.py` provides simple execution identifiers, event records, and logging helpers.
- `tests/` contains independent tests for domain behavior and integrated flows.
- `data/sample/` contains safe, reproducible development data. Real private financial data should not be committed.

The first implementation slice (deterministic data foundation) is now implemented: `models.py`, `data.py`, `validation.py`, `normalization.py`, `synthetic.py`, `analytics.py`, and `verification.py` exist with tests under `tests/` and safe synthetic data at `data/sample/transactions.csv`.

The second slice (deterministic agent runtime) is now implemented under `src/personal_finance_agent/runtime/`: `state.py` (explicit lifecycle state and trajectory), `understanding.py` (deterministic intent recognition), `planning.py` (structured action planning), `tools.py` (the tool/action interface wrapping the analytical capabilities), `checks.py` (verification wiring and trust classification), `replanning.py` (bounded follow-up decisions), `response.py` (grounded deterministic response generation), and `agent.py` (the runtime loop wiring all stages together). The `Agent` class carries a transaction set and exposes `execute(request) -> AgentState`. `config.py` and `observability.py` remain deferred. `main.py` remains the temporary compatibility entry point.
The third slice (provider-neutral LLM abstraction) is now implemented under `src/personal_finance_agent/llm/`: `client.py` (the `LLMClient` abstraction and independent response validation), `types.py` (structured response types including `ToolCall`, `ModelResponse`, `LLMRequest`), `tool_definitions.py` (model-facing metadata for the five analytical tools), `errors.py` (provider-neutral failure vocabulary), and `fake.py` (the deterministic `FakeLLMClient`). `run()` and `Agent` accept an optional `llm_client` injection boundary that records the model identity on state without changing the deterministic lifecycle. No provider SDK, credentials, prompt, or model call is introduced.

The fourth slice (local LLM integration) is now designed but not implemented: `docs/11_local_llm_integration.md` documents the experimental plan to evaluate Ollama running Qwen3 4B locally as the first LLM backend. This is explicitly an experiment — neither Ollama nor Qwen3 4B is a permanent commitment. The provider-neutral `LLMClient` remains the architectural boundary. No Ollama runtime, SDK, model download, API call, or inference code is introduced in this phase.

# 5. Module and Component Mapping

| System Design Component | Implementation Module | Responsibility |
|---|---|---|
| User Interaction / Request Boundary | `main.py` initially; later a small entry-point module | Receive a request and return a response without embedding analysis logic. The final interface is TBD. |
| Input Validation | `validation.py` | Validate request scope, source records, canonical transactions, and action inputs. |
| Request Understanding | `runtime/understanding.py` | Interpret supported requests and identify intent, scope, ambiguity, and next work. Deterministic keyword-matching strategy; provider-neutral boundary for future LLM replacement. |
| Agent State | `runtime/state.py` | Explicit lifecycle state and trajectory recording. |
| Agent Planning | `runtime/planning.py` | Create structured action sequences based on recognized intent and available capabilities. |
| Agent / Decision Layer | `runtime/agent.py` | Maintain state, select actions, observe results, replan, request verification, and decide when to respond. Accepts an optional provider-neutral `llm_client` (injection boundary) without changing the deterministic lifecycle. |
| Tool / Action Interface | `runtime/tools.py` | Dispatch selected analytical capabilities with validated structured inputs. |
| Verification Wiring | `runtime/checks.py` | Map tool results to verification functions and classify trust. |
| Replanning | `runtime/replanning.py` | Bounded follow-up decisions after observing results. |
| Deterministic Analysis Capabilities | `analytics.py` | Perform filtering, totals, grouping, period comparisons, and selected pattern analyses. |
| Data Access / Transaction Data Layer | `data.py` | Load and provide scoped canonical transactions while preserving source references. |
| Result Validation / Verification | `verification.py` | Validate tool outputs and verify important calculations and response claims. |
| Response Generation | `runtime/response.py` | Produce grounded responses from verified or explicitly qualified results. |
| LLM Client Interface | `llm/client.py` | Provider-neutral `LLMClient` abstraction (`model_identifier`, `complete`, `reason`, `generate_response`) plus independent `validate_model_response`; no provider SDK. |
| LLM Types | `llm/types.py` | Provider-neutral structured response types (`ModelResponse`, `ToolCall`, `LLMRequest`); no chain-of-thought stored. |
| LLM Tool Definitions | `llm/tool_definitions.py` | Metadata describing the five analytical tools to a model (name, description, argument schema); no analytical implementation. |
| LLM Errors | `llm/errors.py` | Provider-neutral failure vocabulary (malformed output, unavailable, timeout, context, exhausted sequence). |
| Fake LLM Client | `llm/fake.py` | Deterministic scripted `FakeLLMClient` for tests: sequenced responses, request recording, and scriptable failure modes. |
| Observability | `observability.py` and `logging` | Track execution identifiers, agent steps, actions, statuses, timing, errors, and verification outcomes. |

These are software boundaries within one application, not separate deployable services or packages by necessity.

# 6. Agent Implementation Strategy

The MVP will implement the conceptual runtime as an explicit, inspectable control flow:

```text
Understand
  -> Plan
  -> Act
  -> Observe
  -> Validate
  -> Update State
  -> Replan when necessary
  -> Verify
  -> Respond
```

The implementation should represent each stage as a clear responsibility, even if several stages are implemented by methods in one agent module. The agent should invoke analytical actions through a small registry or dispatch boundary rather than embedding each calculation in the reasoning path.

## 6.1 Runtime mapping

- **Understand:** Convert the request and relevant context into an interpreted intent. The initial implementation uses a narrow deterministic keyword-matching strategy in `understanding.py` (no LLM). This boundary is provider-neutral so a future LLM-based understanding module can replace the deterministic one without redesigning the runtime.
- **Plan:** Create a simple action sequence based on supported intent and available capabilities. A one-action request should not require a general-purpose planning framework.
- **Act:** Dispatch a selected analytical capability with validated structured inputs.
- **Observe:** Read the returned status, result, evidence, warnings, and limitations.
- **Validate:** Check that the result is structurally usable and relevant to the requested scope.
- **Update State:** Append the action, observation, error, and status to in-memory execution state.
- **Replan:** Select another action, ask for clarification, narrow the response, or stop when the current plan is insufficient.
- **Verify:** Run deterministic result checks and confirm that proposed response claims are supported.
- **Respond:** Generate a grounded answer, clarification, limitation, or safe failure.

The agent should not use an orchestration framework for the MVP. A direct Python control flow is easier to inspect and test while the runtime behavior is still being learned.

## 6.2 Where state lives

Execution state lives in memory within the active agent run. The state is passed between runtime stages and is available to observability and verification. Persistent memory is not required for the MVP and remains deferred.

# 7. Agent State Implementation

A simple in-memory state representation is sufficient for the MVP because the requirements establish short-lived execution state and bounded follow-up context but do not require long-term persistence. It avoids introducing a database or memory subsystem before the workflow has been evaluated.

The implementation should use an explicit state object, such as a dataclass, containing conceptual fields like:

| Field | Implementation role |
|---|---|
| `request` | Original user request text or structured request input. |
| `interpreted_intent` | Current intent, scope, periods, dimensions, and requested output. |
| `constraints` | Spending-only scope, period boundaries, supported fields, and response limits. |
| `plan` | Ordered pending and completed conceptual actions. |
| `completed_actions` | Records of actions that were attempted and their statuses. |
| `pending_actions` | Work that remains before a response can be formed. |
| `observations` | Agent observations about results, limitations, and unresolved questions. |
| `analytical_results` | Structured tool results associated with their evidence and scope. |
| `errors` | Categorized failures and recovery information. |
| `assumptions` | Material interpretations such as a period meaning. |
| `verification_status` | Not requested, pending, passed, qualified, failed, or inconclusive. |
| `evidence` | References to transactions, calculations, and result support. |
| `response_status` | Not ready, clarification needed, ready, sent, or failed. |

The state should distinguish planned actions from executed actions, observations from verified results, and a qualified result from a passed result. It should be serializable for debugging if practical, but serialization format and persistence are TBD.

Conversation context for the MVP may be held alongside the active session state. Long-term conversation persistence is not implemented or required at this stage.

# 8. Analytical Tools / Capabilities

The initial analytical capability set should be restrained. The MVP should prioritize operations required by the core use cases and should not implement every possible pattern detector before the data model and basic flow are validated.

## 8.1 Spending total and filtering

- **Purpose:** Calculate spending for a defined period and scope.
- **Inputs:** Canonical transactions, period boundaries, direction inclusion rules, and optional category/merchant filters.
- **Outputs:** Total amount, included transaction references, scope metadata, exclusions, and data-quality warnings.
- **Deterministic behavior:** Select records using explicit boundaries and sum canonical expense amounts using exact monetary arithmetic.
- **Validation expectations:** Dates, amounts, direction, currency scope, and period boundaries must be usable.
- **Error behavior:** Return a structured invalid or incomplete result when required fields are missing or currencies are incompatible.
- **Exposed to agent:** Yes; this is the first analytical capability.

## 8.2 Category spending

- **Purpose:** Group spending by category for a defined scope.
- **Inputs:** Canonical transactions, period/filter scope, and category inclusion rules.
- **Outputs:** Category totals, transaction references, unknown/uncategorized amount, category origin and uncertainty, and warnings.
- **Deterministic behavior:** Aggregate only available category values; do not assign categories inside the arithmetic operation.
- **Validation expectations:** Amount, direction, period, and category availability must be reported.
- **Error behavior:** Return a qualified result when categories are missing or uncertain rather than inventing categories.
- **Exposed to agent:** Yes, if category data is available in the selected MVP data.

## 8.3 Period comparison

- **Purpose:** Compare spending across two explicit periods.
- **Inputs:** Canonical transactions, two period definitions, and consistent inclusion/filter rules.
- **Outputs:** Both totals, absolute difference, percentage change where meaningful, period completeness, evidence references, and warnings.
- **Deterministic behavior:** Calculate both periods independently and derive the difference from those totals.
- **Validation expectations:** Periods must be explicit and comparable; division by zero and incomplete periods require qualification.
- **Error behavior:** Return an invalid or qualified result when period scope or data quality prevents a meaningful comparison.
- **Exposed to agent:** Yes; this is a core MVP capability.

## 8.4 Contributor analysis

- **Purpose:** Identify categories, merchants, or other groups associated with a total or difference.
- **Inputs:** Canonical transactions, grouping dimension, period scope, and direction rules.
- **Outputs:** Ranked group totals, transaction references, reconciliation information where practical, and grouping limitations.
- **Deterministic behavior:** Group and aggregate using the selected canonical field; do not silently merge uncertain merchant identities.
- **Validation expectations:** Grouping field availability and source/derived status must be visible.
- **Error behavior:** Return a qualified result or unsupported status when the grouping dimension is unavailable.
- **Exposed to agent:** Yes, after the basic total and comparison flow is stable.

## 8.5 Recurring-pattern analysis

- **Purpose:** Identify candidate repeated spending patterns.
- **Inputs:** Canonical dates or timestamps, amounts, direction, merchant/description, and sufficient history.
- **Outputs:** Candidate patterns, observed frequency/timing, supporting transaction references, and uncertainty.
- **Deterministic behavior:** Apply explicitly defined pattern logic once the recurrence definition is selected.
- **Validation expectations:** The result must state the history and fields used.
- **Error behavior:** Return insufficient-data or unsupported status when recurrence cannot be evaluated reliably.
- **Exposed to agent:** Deferred until the recurrence definition and baseline are selected.

## 8.6 Unusual/noteworthy activity

- **Purpose:** Identify activity that merits review against an explicit baseline.
- **Inputs:** Canonical amounts, dates, direction, grouping information, and reference history.
- **Outputs:** Candidate noteworthy records or patterns, comparison basis, evidence, and limitations.
- **Deterministic behavior:** Use an explicit comparison basis; do not label activity fraudulent or erroneous.
- **Validation expectations:** A reference period or other basis must exist.
- **Error behavior:** Return insufficient-baseline status rather than guessing what is unusual.
- **Exposed to agent:** Deferred until the definition of unusualness is established.

The initial implementation should begin with spending total/filtering, category spending where supported, and period comparison. Contributor analysis is the next likely capability. Recurring and unusual-activity analysis remain candidates until their definitions are fixed.

# 9. Tool Interface Design

Analytical tools should use structured, provider-neutral inputs and outputs. The exact Python types can be finalized during implementation, but each tool should follow a contract like:

```text
Tool request:
  operation name
  canonical data scope
  filters and period parameters
  inclusion rules

Tool result:
  operation performed
  status
  result values or groups
  scope and parameters
  supporting transaction references
  warnings and limitations
  uncertainty where applicable
```

## 9.1 Tool names and conceptual contracts

| Tool name | Purpose | Input structure | Output structure | Errors | Traceability |
|---|---|---|---|---|---|
| `calculate_spending_total` | Calculate spending for a scope | Transactions, period, filters, direction rules | Total, included references, exclusions, warnings | Missing amount/date, invalid scope, incompatible currency | Included and excluded transaction references |
| `group_spending_by_category` | Group spending by category | Transactions, period, filters, category policy | Category totals, unknown amount, references, uncertainty | Missing categories, invalid scope | Per-category transaction references |
| `compare_spending_periods` | Compare two periods | Transactions, period A, period B, common filters | Both totals, difference, optional percentage, completeness, warnings | Invalid/incomparable periods, missing values | References for both period results |
| `group_spending_by_contributor` | Rank merchants or other contributors | Transactions, period, grouping dimension | Ranked groups, totals, references, grouping warnings | Missing grouping field, ambiguous grouping | Group-to-transaction references |

A tool must validate its own inputs at the boundary, return an explicit status, and avoid returning a plausible value for an invalid request. Tools should not call an LLM or perform hidden interpretation in the MVP.

Tool results should be independently testable without running the agent. The agent should decide which tool to invoke; the tool should execute only the requested deterministic operation.

# 10. Data Implementation

The data implementation should begin with the logical model in `docs/05_data_design.md` and keep source/raw information distinct from canonical transactions and derived results.

## 10.1 MVP source format

The exact source format remains an implementation decision because the previous documents did not select one. For the first local vertical slice, a small CSV or JSON sample is sufficient, with a narrow documented field set covering date, amount, description, direction/type where available, category where available, and source reference.

The chosen sample format must be documented when implementation begins and should not be treated as the final supported input contract. The loader should isolate source-specific parsing from canonical model construction.

## 10.2 Canonical representation

Use an in-memory Python representation based on explicit data structures for the initial slice. It should include at least:

- Stable transaction reference.
- Canonical date and optional timestamp.
- Exact monetary amount.
- Currency when applicable.
- Explicit direction.
- Original and normalized description where available.
- Merchant and category where available.
- Source reference.
- Data-quality and normalization status.

The exact class fields and serialization are implementation details to be finalized from the logical model.

## 10.3 Loading and transformation

The loading flow should be:

```text
Source record
  -> Parse
  -> Structural validation
  -> Semantic validation
  -> Normalize
  -> Categorize or preserve unknown
  -> Canonical transaction
```

Invalid records should receive an explicit outcome: rejected, flagged, excluded from a particular analysis, or retained with a warning. The loader must preserve source references and should not silently change amounts or invent missing fields.

## 10.4 Categorization

The initial implementation may preserve source categories and represent unknown categories. A final categorization strategy is TBD. If a simple deterministic mapping is introduced for the sample data, it must be isolated, traceable, and replaceable rather than embedded in the analytics module.

## 10.5 Derived information

Totals, groups, comparisons, and pattern candidates should initially be computed on demand by analytical capabilities. The implementation should not introduce permanent storage for every derived result.

# 11. Data Loading and Processing Pipeline

The initial pipeline is:

```text
Source Data
  -> Load
  -> Structural Validation
  -> Semantic Validation
  -> Normalize
  -> Categorize / Enrich when supported
  -> Canonical Transactions
  -> Analytical Capabilities
```

Validation occurs at source loading and again at capability boundaries when an analysis has specific requirements. Normalization occurs after a source record is parseable and before it is exposed as a canonical transaction.

Invalid records should not silently disappear. The pipeline should preserve a validation outcome and reason. Depending on the issue and requested analysis, a record may be rejected, retained with a warning, or excluded only from affected calculations.

Analytical capabilities should receive canonical transactions or a scoped view of them, not source-specific records. Evidence references should point back to canonical transaction identities and source references. This preserves traceability while keeping analytics independent of the input format.

The initial pipeline can remain in memory for a local sample. A persistent data-access layer is deferred.

# 12. LLM Integration

No specific LLM provider or model is selected because the previous requirements and designs leave model selection TBD. The implementation should define a provider-neutral reasoning boundary so a model can be introduced without changing the canonical data model or deterministic analytical tools.

## 12.1 LLM responsibilities if introduced

A language model may support:

- Natural-language request understanding.
- Intent and scope interpretation.
- Planning where flexible reasoning is useful.
- Ambiguity detection and clarification wording.
- Grounded response generation from verified results.
- Follow-up reference resolution within available context.

## 12.2 Deterministic responsibilities

The LLM must not be the source of truth for:

- Arithmetic.
- Aggregation.
- Filtering.
- Period calculations.
- Transaction selection.
- Numerical verification.
- Evidence reconciliation.

The model should receive relevant structured analytical results and verification findings rather than the entire raw dataset by default.

## 12.3 Provider and configuration status

Model selection, provider selection, interaction strategy, cost measurement, rate/error handling, and model limitations are TBD. If a provider is introduced later, credentials must come from local configuration or environment variables and must never be hard-coded or committed.

The first deterministic vertical slice can validate data and analytics before a live model is introduced. A provider-neutral request-understanding or response boundary should make that progression possible.

# 13. Prompt / Instruction Strategy

If a language model is introduced, important behavior should be managed through version-controlled instruction artifacts rather than scattered throughout application code.

The instruction strategy should distinguish:

- **System-level instructions:** Overall product scope, safety boundaries, and no-financial-action rules.
- **Agent behavioral instructions:** Understand, plan, act, observe, validate, update, replan, verify, and respond.
- **Tool-use instructions:** Select only supported analytical capabilities and provide complete, validated scope.
- **Grounding instructions:** Use analytical results and evidence; do not invent transactions or numerical values.
- **Verification instructions:** Treat verification state as authoritative for important claims and revise or qualify failed results.
- **Response-generation instructions:** Answer directly, show relevant evidence, distinguish observations from interpretations, and state limitations.

Prompt or instruction versions should be identifiable and testable. The final prompt organization is TBD. The implementation should avoid embedding safety and grounding requirements only in fragile string concatenation or untracked development notes.

# 14. Configuration and Secrets

## 14.1 Configuration

Non-secret configuration may include:

- Input path or sample-data selection.
- Supported analysis feature flags.
- Period and currency-handling options.
- Logging level.
- Model configuration if a model is selected later.
- Runtime limits or thresholds only when justified by a defined requirement.

Configuration should have explicit defaults suitable for local development and should not be scattered across modules.

## 14.2 Secrets

Secrets may include:

- Model or service API keys.
- Credentials.
- Access tokens.
- Other private connection values.

Secrets must not be committed to Git, embedded in source code, placed in sample data, or written to logs. A local environment-variable approach may be sufficient initially; no dedicated secrets-management platform is selected.

The `.gitignore` should exclude local environment files, virtual environments, caches, and other secret-bearing or generated files when implementation changes are made.

# 15. Error Handling Implementation

Errors should be represented explicitly enough for the agent and user boundary to distinguish invalid input, unavailable analysis, verification failure, and unexpected failure without creating an elaborate hierarchy prematurely.

| Error category | Representation and handling |
|---|---|
| Input error | A structured validation outcome with field, scope, and correction information; return a clarification or bounded user error. |
| Data validation error | A record or dataset finding with severity, source reference, and affected analyses; reject, flag, exclude, or qualify as appropriate. |
| Tool error | A failed tool result with operation, status, parameters, and reason; the agent may replan or stop safely. |
| Model/API error | A provider-boundary failure without exposing secrets; retry only when justified, otherwise return a bounded failure or deterministic fallback. |
| Verification failure | A failed or inconclusive verification result that prevents unsupported claims from being presented. |
| Agent execution error | A stateful execution failure with the last completed action and next safe outcome. |
| Unexpected exception | Capture diagnostic context for logs, avoid leaking sensitive data, and surface a clear inability-to-complete response. |

Errors should propagate through structured results or explicit exceptions at module boundaries, then be converted into user-appropriate responses at the request boundary. The agent should not treat an error message as an analytical result.

# 16. Verification Implementation

Verification should be implemented first with deterministic checks.

## 16.1 Tool-result validation

Tool-result validation checks whether the returned result is structurally and contextually usable:

- Required result fields exist.
- The operation and parameters match the requested action.
- The status indicates successful or explicitly qualified completion.
- Referenced transactions exist in the current canonical scope.
- Period and filter metadata are present.
- Warnings and limitations are carried forward.

## 16.2 Numerical and evidence checks

The MVP should support checks such as:

- Recompute spending totals independently from included canonical transactions.
- Validate period comparison arithmetic from the two period totals.
- Check that contributor totals reconcile with the selected aggregate where the grouping is complete.
- Confirm that referenced transactions exist and belong to the stated period and scope.
- Check that direction and currency rules are consistent across related results.

## 16.3 Final-response verification

Final-response verification checks that candidate claims correspond to verified analytical evidence. It should detect or prevent:

- Numbers not present in the verified results.
- Claims using a different period or filter than the analysis.
- Contributors described as causes without evidence.
- Uncertainty or limitations omitted when material.
- Unsupported claims about user motives, fraud, or financial decisions.

Final-response verification need not prove the truth of every natural-language phrase, but it must enforce the distinction between observed evidence and unsupported interpretation. If it fails, the agent should revise, qualify, ask for clarification, or report inability to answer.

# 17. Observability Implementation

The MVP should use simple local observability based on Python logging plus explicit execution events. Distributed tracing infrastructure is not justified yet.

Each execution should have an identifier where practical. Events should capture:

- Request received.
- Input validation result.
- Interpreted intent.
- Plan creation or update.
- Selected action and scoped inputs, excluding unnecessary sensitive values.
- Action start, completion, status, and timing.
- Observation and state transition.
- Replanning or clarification.
- Verification request and outcome.
- Error category.
- Final response status.

Structured event fields should be consistent enough to inspect a trajectory. Model usage, token counts, or cost may be recorded if a provider exposes them later, but no provider-specific fields are required now.

Logs should not contain API keys, credentials, unnecessary raw transaction descriptions, or full sensitive datasets. The exact logging format and retention behavior are TBD.

# 18. Testing Strategy at Implementation Level

Implementation testing should complement, but not replace, the later evaluation plan in `docs/07_testing_and_evaluation.md`.

## 18.1 Unit tests

Unit tests should cover:

- Source parsing and data validation.
- Canonical transaction construction.
- Normalization behavior and preservation of source values.
- Amount and direction semantics.
- Period boundaries.
- Spending totals, grouping, and comparisons.
- Tool input/output contracts.
- Verification checks.
- State transitions and error classification where practical.

Unit tests should not require a live model or external service.

## 18.2 Integration tests

Integration tests should cover:

- Source data through validation, normalization, and canonical transactions.
- Canonical data through an analytical tool and verification.
- Agent state through action dispatch, observation, and response preparation.
- Failure propagation and bounded recovery.

## 18.3 Agent tests

Agent tests should cover:

- Request understanding for supported question categories.
- Appropriate action selection.
- Simple and multi-step planning.
- Grounded response behavior.
- Ambiguity and clarification.
- Follow-up context.
- Verification failure handling.
- Avoidance of unsupported actions and fabricated results.

Where model behavior is involved, tests should use controlled fixtures or a replaceable reasoning boundary so deterministic behavior can still be tested.

# 19. Development Workflow

The intended workflow is:

```text
Design
  -> Implement
  -> Test
  -> Verify
  -> Document
  -> Commit
```

Development should proceed through small vertical slices.

## Slice 1 - Deterministic data foundation

Load a controlled transaction sample, construct canonical transactions, validate fields, calculate spending, and return a result with scope and evidence.

**Status: implemented.** The slice covers CSV loading and validation, canonical normalization, the five baseline analytical capabilities (spending summary, category analysis, period comparison, merchant analysis, largest expenses), deterministic verification, and a committed synthetic dataset. It contains no agent, LLM, agent framework, or runtime dependency beyond the standard library.

## Slice 2 - Natural-language request boundary

**Status: implemented (deterministic runtime).** Interprets a narrow supported request via deterministic keyword matching (`runtime/understanding.py`), selects the corresponding analytical capability through a structured planner (`runtime/planning.py`) and tool interface (`runtime/tools.py`), and returns a grounded answer (`runtime/response.py`). The reasoning mechanism is a narrow, provider-neutral implementation boundary (`runtime/agent.py`) so model selection can be introduced later without redesigning the runtime. Explicit lifecycle state and trajectory are recorded in `runtime/state.py`.

## Slice 3 - Multi-step reasoning and verification

**Status: implemented.** Period comparison, contributor analysis, explicit state, verification wiring (`runtime/checks.py`), and bounded replanning (`runtime/replanning.py`) are all implemented as part of the deterministic runtime.

## Slice 4 - Observability and evaluation preparation

Improve execution event recording, failure visibility, test fixtures, and evaluation-case support.

## Slice 5 - Provider-neutral LLM abstraction

**Status: implemented.** Defines the boundary between the Agent Runtime and any future model without choosing a provider: the `LLMClient` interface (`llm/client.py`), structured response types (`llm/types.py`), tool definitions (`llm/tool_definitions.py`), the error vocabulary (`llm/errors.py`), and the deterministic `FakeLLMClient` (`llm/fake.py`). The runtime accepts an injectable `llm_client` (`run(..., llm_client=...)`, `Agent(transactions, llm_client=...)`) that records the model identity on state while the deterministic lifecycle remains unchanged. No model-powered execution, provider SDK, or prompt exists yet; that is the first model-powered slice.

Each slice should remain runnable and testable before the next slice is added. Advanced capabilities should not block a useful deterministic first slice.

# 20. Git and Version-Control Strategy

The repository should track source code, documentation, tests, configuration templates, and safe sample data. Documentation changes should remain part of the engineering record and should be committed with meaningful scope.

A solo project does not require a complex branch strategy. The default branch and short-lived branches are sufficient unless collaboration needs change. Commits should describe one coherent change, such as a data foundation, an analytical capability, or a verification improvement.

The following should never be committed:

- `.venv/` and other local virtual-environment contents.
- API keys, credentials, tokens, and local secret files.
- Private unredacted transaction data.
- Unreviewed generated logs or sensitive execution traces.
- Large generated artifacts that are not part of the project record.

At minimum, `.venv` and local secret files should be excluded by `.gitignore`. Source code, tests, documentation, `pyproject.toml`, and safe reproducible sample data should be tracked. Generated artifacts should be handled deliberately rather than committed by default.

# 21. Local Development Workflow

The local workflow should use the existing Python and `uv` setup without requiring additional services.

## 21.1 Environment setup

- Use the repository's Python `>=3.12` environment.
- Use `uv` for environment and dependency operations.
- Keep dependencies declared in `pyproject.toml` if any are added.
- Keep secrets outside source control, using local environment configuration if needed.

## 21.2 Running the application

The initial vertical slice may be run through the repository entry point or a module entry point once implemented. The final interface is TBD, so this document does not prescribe a permanent CLI, web interface, or service command.

## 21.3 Running tests

Use Python's standard-library test runner. The project package is installed editable in the uv-managed environment, so tests run from the repository root with:

```text
uv run python -m unittest discover -s tests
```

or, with the project virtual environment already active:

```text
python -m unittest discover -s tests
```

## 21.4 Inspecting logs and sample data

Run the application against safe sample data, inspect local execution logs, and use execution identifiers to follow an agent trajectory. Do not use private financial data in committed examples or logs.

## 21.5 Formatting and linting

No formatter or linter is selected yet. A formatter or linter may be added if repeated implementation work demonstrates a need, but it should not be introduced solely as project decoration.

## 21.6 Git workflow

Keep changes focused, run relevant tests and checks, inspect the diff, and commit only the intended source, test, documentation, and configuration changes.

# 22. MVP Implementation Plan

## Milestone 1 - Data foundation

Define the initial canonical transaction representation, create safe sample data, implement loading, validation, normalization, and source traceability.

**Working increment:** A validated canonical transaction collection can be loaded and inspected.

**Status: complete.** Canonical transactions, CSV loading, explicit validation errors, normalization, and the synthetic sample dataset are implemented and unit-tested.

## Milestone 2 - Deterministic analytics

Implement spending totals, filtering, category grouping where supported, and period comparison using explicit amount and direction semantics.

**Working increment:** Analytical capabilities return structured, testable results with evidence references.

**Status: complete.** Spending summary, category analysis, period comparison, merchant analysis, and largest-expense analysis return frozen dataclass results with explicit totals, status, warnings, currency, and evidence references.

## Milestone 3 - Agent foundation

Implement the single-agent state representation, supported request understanding boundary, simple planning, and action selection.

**Working increment:** A supported request can select an analytical capability through explicit state.

**Status: complete.** `runtime/state.py` provides the explicit lifecycle state and trajectory; `runtime/understanding.py` provides deterministic intent recognition; `runtime/planning.py` produces structured action sequences.

## Milestone 4 - Agent/tool integration

Connect the agent to analytical tools, observations, validation, and response preparation.

**Working increment:** The agent can complete a basic request through an analytical action.

**Status: complete.** `runtime/tools.py` wraps the analytical capabilities; `runtime/agent.py` wires the full loop (understand → plan → execute → observe → verify → replan → respond); observations and errors are recorded explicitly.

## Milestone 5 - Verification

Add deterministic result checks, evidence/reference checks, period consistency checks, and final-response claim checks.

**Working increment:** Important results cannot reach the response stage without an explicit verification outcome.

**Status: complete.** Deterministic result verification (`verification.py`) is wired to tool results through `runtime/checks.py` with trust classification (verified/failed/inconclusive/unverified). The runtime records verification results per action and sets `response_status` to `failed_verification` when any critical check fails.

## Milestone 6 - Grounded responses

Generate understandable responses from verified results, including scope, evidence, assumptions, and limitations. Introduce a selected reasoning provider only if the requirements and implementation plan justify it.

**Working increment:** The agent returns a grounded answer or a clear limitation/clarification response.

**Status: complete (deterministic).** `runtime/response.py` generates concise natural-language responses from verified structured evidence only; unsupported explanations are impossible by construction since the generator reads all numerical values directly from analytical result dataclasses.

## Milestone 7 - Error handling and observability

Add categorized failures, bounded recovery, clarification handling, execution identifiers, action events, verification events, and safe logging.

**Working increment:** An execution can be inspected and failures do not silently become answers.

## Milestone 8 - Evaluation preparation

Create stable fixtures, representative edge cases, agent trajectory records, and interfaces needed by the testing and evaluation phase.

**Working increment:** The implementation is ready for systematic evaluation rather than only manual demonstration.

# 23. Future Implementation Evolution

The MVP boundaries should support later evolution without requiring a complete rewrite:

- **Persistent database:** The data-access boundary and canonical transaction model can later be backed by durable storage if multiple users, history, or volume justify it.
- **Richer data ingestion:** Source-specific loaders can be added before canonical construction without changing analytical capabilities.
- **External APIs:** External sources can be introduced behind controlled data-access and privacy boundaries if requirements approve them.
- **Containerization:** The modular application can later be packaged for another runtime without changing the logical agent or analytical contracts.
- **Hosted deployment:** The request boundary, observability, configuration, and security responsibilities provide future points for operational design.
- **Persistent conversation memory:** The distinction between execution state and conversation context allows persistence to be added only if follow-up requirements justify it.
- **More sophisticated analytics:** Additional tools can implement the same structured result and evidence contract.
- **Additional specialized agents:** A future design could introduce specialized components only if evaluation shows that one agent is insufficient.
- **Multiple users and larger workloads:** Data-access isolation, privacy boundaries, and explicit execution identifiers can be strengthened as operational requirements emerge.

These capabilities are not part of the MVP and should not be implemented merely to demonstrate extensibility.

# 24. Implementation Trade-offs

## 24.1 Simplicity versus extensibility

A small in-process structure is faster to understand and test, while clean module boundaries preserve a path for future change. The MVP should choose simple boundaries rather than future infrastructure.

## 24.2 LLM flexibility versus deterministic correctness

An LLM may improve request interpretation and response fluency, but it is a poor source of truth for arithmetic and filtering. The implementation therefore keeps analytical tools deterministic and treats model output as interpretation that must remain grounded and verified.

## 24.3 In-memory state versus persistent state

In-memory state is easy to inspect and sufficient for one active execution or bounded local session. Persistent state could support longer conversations and repeated analysis but adds privacy, lifecycle, and storage complexity. In-memory state is preferred initially.

## 24.4 Local files versus database

Local sample files are sufficient for a controlled prototype and make test data reproducible. A database would be justified only by persistence, multi-user, volume, or integration requirements that are not yet established.

## 24.5 Single agent versus multi-agent

One agent keeps state, planning, and verification easier to inspect. Multiple agents could divide future responsibilities but add coordination and evaluation complexity. The MVP remains single-agent.

## 24.6 Minimal dependencies versus convenience frameworks

The standard library requires some explicit code but keeps the implementation transparent and avoids framework commitments. A dependency should be added only when a concrete requirement demonstrates that the standard library is insufficient.

## 24.7 Rich observability versus implementation complexity

Detailed traces help evaluate agent behavior, but logging all raw data would add privacy risk and noise. The MVP should record structured lifecycle events and evidence references without unnecessary sensitive payloads.

# 25. Implementation Decisions and Rationale

| Decision | Rationale | Status |
|---|---|---|
| Use Python 3.12+ | The repository already requires Python `>=3.12`, and it supports the domain model, deterministic analytics, and agent state. | Decided |
| Use `uv` for environment/dependency management | `uv` is the existing project workflow and supports reproducible dependency management. | Decided |
| Use a modular in-process application initially | The system design requires logical boundaries but does not require separate services or distributed deployment. | Decided |
| Use a single-agent implementation | The agent design explicitly defines one initial agent; multiple agents are not justified for the MVP. | Decided |
| Use deterministic analytical tools | Requirements require correctness, traceability, and verification for numerical operations. | Decided |
| Use explicit in-memory execution state | The MVP requires short-lived inspectable state, not persistent memory. | Decided |
| Begin with local/synthetic sample data | It supports reproducible development and edge-case testing without assuming access to private banking data. | Decided for initial development |
| Prefer standard-library data handling | `dataclasses`, `datetime`, `decimal`, `csv`, and `json` cover the initial logical model and local pipeline without unnecessary dependencies. | Decided for initial development |
| Use `unittest` initially | It provides unit and integration testing without adding a dependency. | Decided for initial development |
| Represent money as `Decimal` absolute magnitude with an explicit `Direction` | Avoids binary floating-point error for monetary arithmetic and keeps spending semantics explicit; aggregation never mixes currencies. | Decided for the current slice |
| Return structured dataclass results with status, warnings, and evidence references | Deterministic results must be inspectable and verifiable by a later agent layer rather than rendered as prose. | Decided for the current slice |
| Verify analytical results by independent deterministic recomputation | Recomputation, reconciliation, and evidence checks catch inconsistent results without an LLM, as required by the verification design. | Decided for the current slice |
| Use simple local logging initially | The MVP needs execution visibility but not distributed tracing infrastructure. | Decided for initial development |
| Keep the input interface provisional | Earlier requirements leave the interface TBD; the first vertical slice can use a local entry point without finalizing CLI/web/service design. | Tentative |
| Select an exact source format | A small CSV sample (`data/sample/transactions.csv`) is sufficient for the deterministic foundation; the final user-facing input contract remains open. | Decided for the current slice |
| Select an LLM/model provider | Prior documents leave model selection and provider unresolved. | TBD |
| Select categorization implementation | Data quality and evaluation must inform whether rules, mappings, model-based, or hybrid categorization is appropriate. | TBD |
| Add runtime dependencies beyond the standard library | No current requirement justifies a specific additional package. | TBD |
| Select persistent storage | The MVP does not require persistence beyond active execution or controlled local data. | TBD |
| Select deployment, containerization, and external integrations | These are future options without current MVP requirements. | TBD |

# 26. Open Questions / TBD

The following implementation questions remain unresolved:

- Which exact LLM or reasoning model, if any, will be used?
- Which provider, if any, will supply that model?
- What final runtime dependencies are justified after the first vertical slice?
- What exact input format will the MVP accept as its user-facing contract?
- How will categorization be implemented and evaluated?
- What exact tool input/output representations will be adopted?
- How should prompts or instruction artifacts be organized once a model is selected?
- Is persistent storage required after initial workflow evaluation?
- What interface should be finalized for the MVP?
- What deployment target is appropriate after local behavior is validated?
- Which observability tooling, event format, and retention policy should be selected?
- What evaluation tooling is needed beyond standard-library tests?
- Which external integrations, if any, will later be justified?
- What runtime limits, cost controls, and model-failure policies are appropriate?
- Which recurring and unusual-activity analyses should be implemented after core totals and comparisons are validated?

These questions should be resolved through implementation evidence, testing, and evaluation rather than by adopting technologies in advance.

# 27. Handoff to Testing and Evaluation

This implementation plan is intended to produce a working system whose behavior can be systematically tested. It establishes a small, modular, single-agent application with deterministic analytical capabilities, explicit in-memory execution state, source-to-canonical data handling, independent verification, and simple observability.

The next document is `docs/07_testing_and_evaluation.md`. It should define:

- Testing strategy and test levels.
- Test cases and fixtures.
- Evaluation dataset and ground truth.
- Agent trajectory evaluation.
- Numerical correctness.
- Tool-selection evaluation.
- Groundedness.
- Hallucination and fabrication avoidance.
- Ambiguity handling.
- Failure recovery.
- Human evaluation.
- Automated evaluation.
- Metrics.
- Regression evaluation.

Evaluation should measure whether the implemented system actually satisfies the requirements and approved designs. A working demo is necessary but is not sufficient evidence of correctness, groundedness, reliability, or useful agent behavior.
