# 1. Testing and Evaluation Overview

This document defines how the Personal Finance Agent will be tested, evaluated, validated, and measured. It builds on the problem and success criteria in `docs/01_problem_and_objectives.md`, the requirements in `docs/02_requirements.md`, the architecture and responsibilities in `docs/03_system_design.md`, the runtime in `docs/04_agent_design.md`, the data model in `docs/05_data_design.md`, and the implementation approach in `docs/06_implementation.md`.

**Testing** asks whether the software behaves correctly according to its specification. It is primarily concerned with deterministic behavior, component contracts, failure handling, and repeatable expected outcomes.

**Evaluation** asks how well the complete agent performs realistic tasks. It considers request understanding, action selection, planning, groundedness, ambiguity handling, usefulness, recovery, conversational continuity, and the quality of the final interaction.

Both are necessary. Numerical correctness alone does not establish that the agent understood the request, selected an appropriate analysis, explained the result, handled uncertainty, or avoided unsupported claims. Conversely, a fluent response does not establish that the underlying calculation is correct. A working system is not necessarily a reliable system.

# 2. Evaluation Objectives

The project should ultimately establish evidence for the following qualities:

- **Functional correctness:** Supported requests, inputs, outputs, and error paths behave according to requirements.
- **Analytical correctness:** Filtering, grouping, comparisons, pattern analyses, and inclusion rules operate on the intended data.
- **Numerical correctness:** Reported totals, differences, percentages, and rankings agree with trusted calculations.
- **Agent behavior correctness:** The agent understands intent, plans appropriate work, selects suitable capabilities, observes results, verifies important outputs, and stops appropriately.
- **Groundedness:** Important claims are supported by available transaction data, analytical results, and evidence references.
- **Reliability:** The system behaves predictably and does not silently fail or fabricate results.
- **Robustness:** The system handles incomplete, malformed, ambiguous, conflicting, and adversarial inputs safely.
- **Usefulness:** Responses are understandable, relevant, and practically useful for reviewing personal spending.
- **Safety:** The agent respects financial-action boundaries, communicates uncertainty, and avoids unsupported financial advice or causal claims.
- **Predictable failure behavior:** When a task cannot be completed, the system clarifies, qualifies, or declines rather than inventing an answer.
- **Maintainability and regression protection:** Improvements do not silently break previously validated data, analytical, agent, or safety behavior.

These objectives operationalize the qualitative success criteria and requirements established in the previous documents. Exact quantitative thresholds are not defined yet.

# 3. Testing and Evaluation Layers

The project should use several complementary layers:

1. **Data Tests:** Validate parsing, canonical representation, quality handling, normalization, categorization, and traceability.
2. **Unit Tests:** Test small deterministic functions and state/verification logic in isolation.
3. **Analytical/Tool Tests:** Test each analytical capability independently of the agent.
4. **Integration Tests:** Test contracts and data flow between modules.
5. **Agent Behavior Tests:** Test intent understanding, planning, action selection, observation, verification, replanning, and stopping.
6. **End-to-End Tests:** Test complete user request to response scenarios.
7. **Evaluation Dataset:** Run representative tasks with expected intent, evidence, results, and response characteristics.
8. **Human Evaluation:** Assess clarity, usefulness, relevance, groundedness, and uncertainty where automated checks are insufficient.
9. **Regression Evaluation:** Re-run preserved cases after changes to data processing, tools, prompts, models, state, verification, or response behavior.

Each layer answers a different question. A passing unit test cannot prove that the agent selected the right tool, and a good end-to-end example cannot prove that every period comparison is correct.

# 4. Test Pyramid

The testing strategy should contain:

- Many fast deterministic unit and data tests.
- Focused analytical and tool tests with exact expected results.
- Fewer integration tests covering important component contracts.
- Fewer expensive or variable agent and end-to-end tests.
- Broader evaluation datasets for realistic behavior and edge cases.

Agent systems should not rely exclusively on end-to-end tests. End-to-end tests are valuable but can be slow, difficult to diagnose, sensitive to model or prompt changes, and insufficiently precise about whether a failure came from data, analytics, planning, tool selection, verification, or response generation.

# 5. Data Testing

Data tests should use controlled records with known expected outcomes. They should cover:

- Valid transaction records.
- Missing identifiers, dates, amounts, descriptions, merchants, categories, and direction values.
- Malformed dates and amounts.
- Invalid or conflicting transaction direction.
- Duplicate records.
- Inconsistent descriptions and merchant representations.
- Unknown and uncertain categories.
- Refunds and reversals.
- Transfers.
- Income mixed with expenses.
- Multiple currencies where supported or explicitly rejected.
- Empty datasets.
- Very large datasets within the intended test scope.

Data tests should verify:

- Structural and semantic validation.
- Normalization without loss of source evidence.
- Canonical transaction construction.
- Explicit amount and direction semantics.
- Categorization origin and uncertainty.
- Source-to-canonical traceability.
- Appropriate handling of rejected, flagged, excluded, and retained-with-warning records.

# 6. Unit Testing

Unit tests should target deterministic components and small state transitions. Potential areas include:

- Source parsing.
- Field validation.
- Amount and direction normalization.
- Date and period-boundary calculations.
- Description and merchant normalization.
- Categorization mappings, if selected.
- Transaction filtering.
- Spending aggregation.
- Category and merchant calculations.
- Period comparison arithmetic.
- Recurring-pattern logic, once defined.
- Unusual-activity logic, once defined.
- Analytical-result validation.
- Verification logic.
- Agent state updates and error classification.

Expected outputs should be deterministic wherever possible. Tests should use exact fixtures and should not require a live model or external service for domain calculations.

# 7. Analytical / Tool Testing

Analytical capabilities must be tested independently of the agent. Each tool should be tested with valid inputs, invalid inputs, boundary conditions, empty results, expected outputs, traceability, and error behavior.

## 7.1 Spending total

Verify that the returned total equals the expected sum of included canonical expense transactions. Tests should cover period boundaries, direction exclusions, refunds, transfers, missing amounts, duplicate flags, and evidence references.

## 7.2 Period comparison

Verify that:

- Both periods select the correct transactions.
- Both totals are correct.
- The absolute difference is correct.
- The percentage change is correct when defined.
- Complete and incomplete periods are identified.
- Shared filters and inclusion rules are applied consistently.

## 7.3 Category analysis

Verify that category totals match the relevant grouped transactions and reconcile with the overall total where the category coverage is complete. Tests should expose unknown, uncertain, and uncategorized amounts rather than silently forcing reconciliation.

## 7.4 Contributor analysis

Verify that identified contributors correspond to the selected merchant or grouping field, that their totals are correct, and that claimed contributors actually explain the reported change when the result makes that claim.

Recurring and unusual-activity tools require tests once their definitions, baselines, and minimum data requirements are selected.

# 8. Verification Testing

Verification mechanisms must themselves be tested rather than assumed to work.

Test cases should include:

- A correct result that passes verification.
- An incorrect total that fails verification.
- An incomplete result that is flagged.
- Inconsistent period or filter metadata that is detected.
- Evidence references that do not exist or do not belong to the stated scope.
- A contributor result that does not reconcile with the claimed difference.
- An unsupported interpretation that is rejected or qualified.
- Missing evidence that prevents verification.
- A final response containing a number not present in verified results.
- A final response that omits a material limitation.

**Analytical-result verification** checks the operation, values, scope, and evidence. **Generated-response verification** checks whether user-facing claims remain faithful to verified results and do not introduce unsupported interpretations.

# 9. Integration Testing

Integration tests should verify that component contracts remain compatible across the main flows:

- Data loader to validator.
- Validator to canonical transaction representation.
- Canonical transactions to analytical capability.
- Analytical capability to verification.
- Agent to analytical capability/action dispatch.
- Analytical result back to agent state and observation.
- Verified result to response generation.
- Errors from lower layers to bounded user-facing behavior.
- Observability events across an execution.

Integration tests should preserve source references, status, warnings, assumptions, and verification state across boundaries. They should not depend on a particular deployment topology.

# 10. Agent Behavior Testing

Agent tests should focus on the internal runtime as well as the final response.

## 10.1 Request understanding

Test whether the agent identifies the intended measure, period, dimension, comparison, constraints, missing information, and supported/unsupported scope.

## 10.2 Action/tool selection

Test whether the selected analytical capability matches the interpreted request and whether the action receives appropriate scope and parameters.

## 10.3 Planning

Test simple requests requiring one main action and multi-step requests requiring ordered filtering, comparison, grouping, contributor analysis, and verification.

## 10.4 Execution

Test whether the agent executes selected actions with valid inputs and records status and results rather than assuming success.

## 10.5 Observation

Test whether the agent correctly interprets successful, empty, partial, invalid, and failed action results.

## 10.6 Verification

Test whether important numerical and analytical outputs are sent through verification before response generation.

## 10.7 Replanning

Test whether the agent changes course when data is missing, a capability fails, evidence is insufficient, or verification fails.

## 10.8 Stopping behavior

Test whether the agent stops after the question is answered and does not perform unnecessary actions or continue after an unrecoverable failure.

# 11. Ambiguity and Clarification Testing

Ambiguity tests should include:

- "How much did I spend recently?"
- "Why did spending go up?"
- "What did I spend on food?"
- "Show me unusual spending."
- Follow-ups with unclear references to earlier results.

Tests should determine whether the agent:

- Infers reasonable context when the risk of misunderstanding is low.
- States assumptions that materially affect the result.
- Asks for clarification when competing interpretations change correctness.
- Avoids asking for clarification when available context is sufficient.
- Refuses or bounds unsupported requests.
- Avoids making a misleading assumption merely to continue.

The evaluation should not reward clarification for every vague phrase. The desired behavior is useful judgment, not maximum questioning.

# 12. Groundedness Testing

Groundedness tests determine whether response claims are supported by the available data and analytical evidence. A response should not:

- Invent transactions.
- Invent numerical values.
- Invent merchants or categories.
- Claim unsupported causes.
- Contradict analytical results.
- Introduce facts not present in the available data.
- Hide material uncertainty or exclusions.

Evaluation cases can classify response claims as:

- **Fully supported:** The claim follows from the available evidence and verified result.
- **Partially supported:** The claim contains a supported observation but overstates scope or certainty.
- **Unsupported:** The claim has no sufficient evidence.
- **Contradicted by evidence:** The claim conflicts with the transaction data or verified result.

These categories can support automated checks for numerical and reference claims and human review for interpretation quality.

# 13. Hallucination / Fabrication Testing

Targeted fabrication tests should ask about:

- A merchant that is not present.
- A period with no data.
- A transaction that is not present.
- An amount absent from the dataset.
- Incomplete data that cannot support the requested conclusion.
- A causal explanation not established by the records.
- A request to ignore system boundaries or invent a plausible answer.

Expected behavior is to acknowledge missing evidence, state limitations, ask clarification where appropriate, and avoid inventing an answer. A confident response with plausible but unsupported details is a failure even if it sounds useful.

# 14. Conversational Context Testing

Follow-up tests should include:

```text
User: How much did I spend in August?
Follow-up: What about restaurants?
```

The agent should resolve the second request against the established period and relevant analytical context, then perform only the additional analysis needed.

Test cases should cover:

- Valid follow-up references.
- Context-dependent periods and filters.
- A changed topic that should reset or narrow context.
- Ambiguous references to multiple earlier results.
- Explicit context reset.
- Multiple sequential follow-ups.
- Follow-up after a failed or qualified result.

These tests should use bounded session context and should not assume long-term memory.

# 15. Failure Recovery Testing

Failure tests should include:

- Analytical action failure.
- Empty result.
- Malformed tool output.
- Incomplete data.
- Verification failure.
- Invalid plan.
- Unavailable analytical capability.
- Model or reasoning failure where applicable.
- Unexpected internal exception.

The expected behavior is that the agent recognizes the failure, updates state, replans when appropriate, retries only when justified, asks the user when necessary, or stops safely. It must not fabricate a successful result after a failed action.

# 16. End-to-End Testing

Complete user-to-response scenarios should include:

### Scenario 1 - Basic spending total

"How much did I spend last month?"

Validate request scope, data loading, deterministic total, evidence, verification, and response clarity.

### Scenario 2 - Period comparison

"How did my spending change compared with the previous month?"

Validate comparable periods, totals, difference, completeness, and grounded explanation.

### Scenario 3 - Spending increase explanation

"Why did my spending increase?"

Validate multi-step planning, contributors, evidence-supported interpretation, and avoidance of causal claims.

### Scenario 4 - Category analysis

"What were my biggest spending categories?"

Validate category availability, grouping, unknown values, totals, and limitations.

### Scenario 5 - Unusual spending

"Find unusual spending."

Validate baseline availability, explicit comparison basis, qualification, and safe interpretation.

### Scenario 6 - Ambiguous request

A request such as "How much did I spend recently?"

Validate focused clarification and avoidance of arbitrary scope.

### Scenario 7 - Multi-action question

A request that requires comparison followed by contributor analysis.

Validate action order, intermediate observations, state, and final verification.

### Scenario 8 - Verification failure

A scenario where periods, evidence, or tool output cannot support the requested conclusion.

Validate safe recovery, limitation reporting, and no fabricated result.

# 17. Evaluation Dataset

The dedicated evaluation dataset should contain representative tasks rather than random examples. Each evaluation case should conceptually include:

- Case ID.
- Transaction dataset or controlled data reference.
- User request.
- Expected intent.
- Expected analytical operation or operations.
- Expected numerical results where applicable.
- Expected evidence or transaction references.
- Expected response characteristics.
- Known edge conditions.
- Expected clarification, failure, or safety behavior.

The dataset should contain normal supported tasks, incomplete and ambiguous cases, malformed-data cases, unsupported requests, verification failures, follow-ups, and adversarial or fabrication-provoking cases. It should include both cases designed for deterministic ground truth and cases requiring human judgment.

The actual dataset, split strategy, size, and maintenance process are TBD. Private financial data must not be used without appropriate authorization and handling.

# 18. Ground Truth

For deterministic questions, ground truth can be calculated directly from the transaction data using independently checked calculations. Examples include spending totals, category totals, contributor totals, period differences, and percentages where defined.

For agent behavior, ground truth may include:

- Expected intent.
- Acceptable analytical approach.
- Required or acceptable evidence.
- Expected safety behavior.
- Required clarification or acceptable assumption.
- Acceptable response characteristics.
- Whether verification is required before responding.

Open-ended responses may have multiple valid wordings. Evaluation should therefore assess claims, evidence, scope, safety, relevance, and usefulness rather than require exact wording.

# 19. Evaluation Case Categories

The evaluation dataset should include:

1. **Simple factual queries:** Basic totals and direct lookups.
2. **Aggregation queries:** Totals, counts, and grouped spending.
3. **Category queries:** Category rankings and category comparisons.
4. **Merchant queries:** Merchant or contributor analysis.
5. **Temporal comparisons:** Period-over-period questions.
6. **Multi-step analytical questions:** Requests requiring multiple actions.
7. **Pattern detection:** Recurring or trend-related requests.
8. **Unusual activity:** Baseline-dependent noteworthy-activity requests.
9. **Ambiguous requests:** Requests requiring inference, assumptions, or clarification.
10. **Unsupported requests:** Questions outside transaction/spending analysis or safety boundaries.
11. **Missing-data scenarios:** Records or fields insufficient for the requested result.
12. **Verification failures:** Results that cannot be checked or do not reconcile.
13. **Follow-up questions:** Requests depending on conversational context.
14. **Adversarial/fabrication-provoking questions:** Requests designed to tempt unsupported claims or boundary violations.

These categories matter because a system can perform well on simple totals while failing on context, uncertainty, safety, or multi-step work.

# 20. Evaluation Metrics

Metrics are candidate measures, not final thresholds.

## 20.1 Numerical accuracy

Measures whether reported numerical values match independently calculated expected results. It matters because incorrect numbers directly undermine spending analysis.

## 20.2 Intent accuracy

Measures whether the agent identifies the expected analytical intent, scope, and constraints. It matters because an accurate calculation for the wrong question is still a failure.

## 20.3 Tool/action selection accuracy

Measures whether the agent selects appropriate capabilities and supplies suitable parameters. It matters because tool choice controls the analytical path and evidence available.

## 20.4 Task completion rate

Measures the proportion of supported cases completed with an acceptable result or response. It should distinguish successful answers from safe clarifications and legitimate inability-to-answer outcomes.

## 20.5 Groundedness

Measures the proportion or severity-weighted share of response claims supported by transaction data, analytical results, and verification evidence.

## 20.6 Fabrication rate

Measures unsupported or invented transaction facts, numerical values, merchants, causes, or evidence. A lower rate is required for reliable use.

## 20.7 Verification success

Measures whether important outputs were sent through appropriate checks and whether failed checks prevented unsupported claims.

## 20.8 Recovery success

Measures whether the agent recognizes failures, updates state, replans appropriately, and reaches a safe outcome when possible.

## 20.9 Clarification quality

Measures whether clarification is requested when necessary, avoids unnecessary questioning, and asks for information that can actually resolve the ambiguity.

## 20.10 Response relevance

Measures whether the response addresses the user's actual request rather than a related or assumed question.

## 20.11 Response usefulness

Measures whether a person can understand and use the result, including evidence, scope, assumptions, and limitations.

## 20.12 Efficiency

Potential efficiency measures include number of actions, execution time, model calls where applicable, token usage where measurable, and computational cost. These measures should be interpreted alongside correctness and groundedness rather than optimized in isolation.

Exact definitions, aggregation methods, and thresholds are TBD.

# 21. Human Evaluation

Human judgment is useful for qualities that are difficult to measure reliably through exact assertions. Human reviewers may assess:

- Clarity.
- Usefulness.
- Relevance.
- Groundedness.
- Interpretation quality.
- Appropriate uncertainty.
- Naturalness of conversational interaction.
- Whether the response distinguishes observation from unsupported explanation.

A simple conceptual rubric can score each response on a small ordered scale for:

1. Directness and relevance.
2. Evidence and groundedness.
3. Clarity and usefulness.
4. Uncertainty and limitation handling.
5. Safety and boundary compliance.

The exact scale, reviewer instructions, sampling, and agreement process are TBD. Human evaluation should supplement deterministic tests and automated checks, not replace them.

# 22. Automated Evaluation

Automated evaluation should be prioritized for:

- Numerical correctness.
- Deterministic analytical outputs.
- Tool execution and status.
- Schema and result validity.
- Validation and verification behavior.
- Expected intent classification where measurable.
- Evidence-reference consistency.
- Groundedness checks for numerical and identifiable claims where reliably automatable.
- Regression comparisons.
- Action counts and execution timing where relevant.

Subjective qualities such as usefulness, naturalness, and nuanced interpretation may require human review. Automated checks should report uncertainty rather than create false precision when a claim cannot be reliably classified.

# 23. Agent Trajectory Evaluation

Evaluation should inspect how the agent reached an answer, not only the final response. A trajectory may include:

- Interpreted intent.
- Plan and plan updates.
- Selected actions and parameters.
- Action sequence.
- Action results and observations.
- State transitions.
- Validation outcomes.
- Verification requests and results.
- Replanning decisions.
- Unnecessary actions.
- Final response and evidence.

Trajectory evaluation matters because two agents may produce the same final answer while one follows a reliable, verifiable process and the other reaches it through an invalid or fragile path. A trajectory that produces the right answer for the wrong reason may fail under a nearby input.

# 24. Regression Testing

Previously validated cases should be preserved and rerun whenever the system changes, including changes to:

- Prompts or instructions.
- Model or provider.
- Analytical logic.
- Tools and tool contracts.
- Agent state or planning.
- Verification.
- Data parsing, normalization, or categorization.
- Response generation.

Regression evaluation should protect deterministic correctness, safety boundaries, groundedness, ambiguity handling, conversational context, and failure recovery. Improvements in one area must not silently break another.

# 25. Adversarial and Edge-Case Evaluation

Deliberate stress tests should include:

- Misleading or ambiguous transaction descriptions.
- Missing information.
- Conflicting information.
- Unusually large amounts.
- Empty periods.
- Extremely large values.
- Unusual category distributions.
- Unsupported questions.
- Requests for investment, tax, credit, payment, or other prohibited functionality.
- Prompts attempting to make the agent invent information.
- Requests to ignore system boundaries.
- Tool results designed to be incomplete or inconsistent.

The purpose is robustness and safe failure, not merely benchmark performance. Results should show whether the agent recognizes uncertainty, protects boundaries, and avoids fabricated outputs.

# 26. Performance and Cost Evaluation

The project should eventually measure:

- Response latency.
- Number of analytical actions.
- Number of model calls where applicable.
- Token usage where applicable.
- Computational cost where measurable.
- Dataset size relative to execution time.
- Verification and recovery overhead.

No arbitrary performance or cost targets are set here. The initial goal is to make the relevant quantities observable so later targets can be based on actual workload and use-case evidence.

# 27. Evaluation Workflow

The evaluation lifecycle is:

```text
Evaluation Dataset
  -> Run System
  -> Capture Trajectory
  -> Compare Results with Ground Truth
  -> Calculate Metrics
  -> Human Review Where Needed
  -> Analyze Failures
  -> Improve System
  -> Re-run Evaluation
```

Evaluation is an iterative engineering loop. Results should be versioned or otherwise associated with the implementation, data, instructions, model configuration, and evaluation case set used for the run.

# 28. Failure Analysis

For each failed or materially weak case, capture:

- Case ID.
- User request.
- Expected behavior.
- Actual behavior.
- Failure category.
- Root-cause hypothesis.
- Affected component.
- Severity.
- Proposed fix.
- Regression test or evaluation case required.

Possible failure categories include:

- Data issue.
- Analytical bug.
- Tool-selection error.
- Planning error.
- State or context error.
- Verification failure.
- Hallucination or fabrication.
- Unsupported assumption.
- Prompt or model issue.
- Integration failure.
- Observability gap.

Failure analysis should identify the earliest stage at which the behavior diverged from the expected trajectory. Changing the model should not be treated as the default solution when the actual cause is a data, tool, verification, or state defect.

# 29. Evaluation-Driven Improvement

Evaluation results should drive targeted engineering changes. Possible changes include:

- Data-processing and normalization corrections.
- Analytical logic or period-boundary fixes.
- Tool-interface improvements.
- Agent instructions or planning behavior.
- Verification checks.
- Error handling and recovery.
- Context construction.
- Model selection or interaction strategy.
- Response-generation constraints.

Each change should identify the failure it addresses and should be followed by the relevant regression tests and evaluation cases. Improvements should be judged by their effect across the suite, not by one favorable example.

# 30. Initial Testing Strategy

Testing and evaluation should be introduced in phases proportional to the MVP.

## Phase 1 - Deterministic data and analytical tests

Test parsing, validation, normalization, canonical transactions, spending totals, filters, grouping, and period comparisons with exact expected results.

## Phase 2 - Tool and verification tests

Test structured tool contracts, evidence references, result validation, numerical recomputation, reconciliation, and final-response claim checks.

## Phase 3 - Basic agent behavior tests

Test supported request understanding, action selection, simple planning, clarification, grounded response behavior, and stopping.

## Phase 4 - End-to-end evaluation dataset

Run representative user-to-response cases covering normal tasks, missing data, ambiguity, safety boundaries, and multi-step analysis.

## Phase 5 - Trajectory evaluation and failure analysis

Capture execution state and action sequences, inspect failures, and classify root causes.

## Phase 6 - Regression suite

Preserve validated deterministic, agent, safety, and end-to-end cases and rerun them after material changes.

## LLM-driven loop evidence (DEC-023, recorded 2026-09-11)

The bounded LLM-driven execution loop (`runtime/llm_loop.py`, DEC-023,
provisional/experimental, awaiting review) is covered deterministically by
`tests/test_llm_loop.py`: 35 tests, all passing with `FakeLLMClient`
(no Ollama required); full suite 210/210 passing. The suite covers single and
multiple tool calls, successive replanning, unknown tools, invalid/missing
arguments, invalid period format, reversed periods (rejected at semantic
validation, not normalized — order defines
`absolute_difference = total_b - total_a`), malformed/empty model output,
genuine failed verification (patched `verify_for`, kept distinct from the
currency-anchored grounding rejection tests), inconclusive verification,
model timeout/unavailability, exhausted responses, model-step and tool-call
budgets, repeated identical calls
(`spending_summary(period="2025-08")`, bound `max_consecutive_repeats=2`
on identical tool+args), grounded finals, unsupported-figure fallback,
correct-number/wrong-explanation pass-through (accepted MVP limitation),
provider neutrality (no Ollama import in the loop), hybrid pending-action
consume-by-name + gap-fill through execute -> verify with budget checks, the
deterministic `run()` regression, and raw-transaction exclusion from model
context. Loop bounds: `max_model_steps=6`, `max_tool_calls=4`,
`max_consecutive_repeats=2`, `retry_invalid=1` (same-step inner retry).
Live `qwen3:1.7b` results are recorded in `docs/11_local_llm_integration.md`
(Experiment 6), not here, since live-model behavior is non-deterministic.

# 31. Testing and Evaluation Decisions

| Decision | Rationale | Status |
|---|---|---|
| Deterministic analytics must have automated tests | Numerical and data-processing correctness are hard requirements and have reproducible expected results. | Decided |
| Analytical capabilities must be tested independently of the agent | Tool defects must be distinguishable from request-understanding or planning defects. | Decided |
| Important numerical results require verification tests | Verification is a first-class design responsibility and must itself be trusted through testing. | Decided |
| Agent behavior requires dedicated evaluation | Final-response correctness alone does not establish correct intent, planning, tool selection, or recovery. | Decided |
| Final responses should be evaluated for groundedness | Responses must distinguish evidence from unsupported interpretation. | Decided |
| Agent trajectories should eventually be inspectable | The project needs to evaluate process quality, state transitions, verification, and unnecessary actions. | Decided |
| Evaluation should include edge cases | Missing, malformed, ambiguous, conflicting, and adversarial inputs are part of the problem. | Decided |
| Regression testing should protect improvements | Changes to models, prompts, tools, data, or verification can introduce cross-cutting regressions. | Decided |
| Human evaluation supplements automated evaluation | Clarity, usefulness, and nuanced interpretation cannot all be reduced to exact assertions. | Decided |
| Select an evaluation platform or framework | No current requirement justifies a specific external evaluation platform. | TBD |
| Define final metrics and thresholds | Metrics depend on implemented capabilities, observed workloads, and evaluation data. | TBD |

# 32. Open Questions / TBD

The following testing and evaluation questions remain unresolved:

- What exact evaluation dataset will be used?
- How large should the dataset be, and how should it be split or versioned?
- What exact numerical, groundedness, reliability, recovery, and usefulness metrics will be adopted?
- What quantitative thresholds are appropriate for each supported use case?
- What human-evaluation rubric, reviewer guidance, and sampling process should be used?
- Which groundedness checks can be automated reliably?
- How will trajectories be captured, stored, compared, and reviewed?
- What performance targets should be defined after actual workload is observed?
- What cost targets should be defined if model-based computation is introduced?
- What adversarial test suite is required for the selected interface and reasoning mechanism?
- What evaluation tooling, if any, is justified beyond the project test suite?
- How should different models or providers be compared if more than one is evaluated?
- How frequently should regression evaluation run during development?
- How should real or anonymized data be incorporated without weakening privacy or reproducibility?
- Which pattern-detection capabilities require specialized evaluation cases?

These questions remain TBD and should be resolved through implementation experience and evidence rather than by selecting evaluation infrastructure prematurely.

# 33. Handoff to Deployment and Operations

This document establishes how system correctness and agent quality will be measured. It defines testing layers, deterministic and analytical tests, verification tests, integration and agent behavior tests, ambiguity and groundedness checks, fabrication and failure-recovery tests, end-to-end scenarios, evaluation datasets, ground truth, candidate metrics, human and automated review, trajectory inspection, regression protection, performance observation, and failure analysis.

The next document is `docs/08_deployment_and_operations.md`. It should define:

- Deployment stages.
- Environments.
- Configuration.
- Runtime requirements.
- Observability.
- Monitoring.
- Alerting.
- Reliability.
- Cost management.
- Security operations.
- Incident handling.
- Release process.
- Rollback.
- Maintenance.
- Future production evolution.

Deployment decisions should be based on the actual implemented system and evaluation results rather than infrastructure assumptions. A deployment plan should preserve the testing, observability, privacy, safety, and rollback expectations established here.
