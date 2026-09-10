# 1. Agent Design Overview

This document defines the internal design of the Personal Finance Agent. It derives agent behavior from `docs/01_problem_and_objectives.md`, the requirements in `docs/02_requirements.md`, and the system boundaries and logical components in `docs/03_system_design.md`.

In this project, an **agent** is a single decision-making component that interprets a user's analytical request, determines what work is needed, selects appropriate analytical capabilities, observes their results, manages task state, decides whether more work is required, verifies important results, and produces a grounded response. The agent is not the source of truth for transaction arithmetic when a reliable analytical capability can perform that calculation.

A conventional deterministic program can execute a predefined sequence of operations for known inputs. The agent is needed here because the requested analysis can vary by question, context, available data, and intermediate results. The agent must decide which supported operations are relevant and how to respond when the request is ambiguous, incomplete, unsupported, or not answered by the first analysis. This makes an iterative runtime more appropriate than a single fixed request-to-response step.

The design distinguishes three levels of responsibility:

- **System-level responsibilities:** Input boundaries, validation, data access, analytical capability execution, verification, response delivery, privacy boundaries, and observability.
- **Agent-level responsibilities:** Intent understanding, planning, action selection, task state, observation, ambiguity handling, replanning, interpretation, and deciding when a response is ready.
- **Analytical/tool responsibilities:** Deterministic filtering, arithmetic, aggregation, grouping, period comparison, and supported pattern analysis, with traceable results and status.

The initial design is for one personal finance agent. It does not introduce multiple agents, persistent memory, a specific model, a prompting framework, or any other implementation technology.

# 2. Agent Responsibilities and Boundaries

## 2.1 Agent responsibilities

The agent is conceptually responsible for:

- Understanding the user's analytical intent.
- Determining the relevant time period, categories, merchants, dimensions, and constraints.
- Identifying information required to answer the request.
- Deciding what action should happen next.
- Selecting appropriate available analytical capabilities.
- Decomposing multi-step requests into a reasonable sequence of actions.
- Maintaining task state during an execution.
- Observing action results, status, limitations, and errors.
- Determining whether more analysis is required.
- Handling ambiguity and requesting clarification when necessary.
- Handling analytical failure and deciding whether to retry, revise, narrow, or stop.
- Deciding when verification is required and whether its result is sufficient.
- Interpreting verified analytical results in relation to the request.
- Generating a response grounded in the available evidence.
- Stopping when the question has been adequately answered.

## 2.2 Agent boundaries

The agent should not be responsible for:

- Blindly performing arithmetic when a deterministic analytical capability is available.
- Inventing transaction records, values, categories, evidence, or analytical results.
- Modifying financial records or transaction data as an external side effect.
- Moving money or executing payments.
- Performing automated banking operations.
- Making investment decisions or providing investment advice.
- Performing tax filing or tax advisory work.
- Making loan or credit decisions.
- Recommending financial products.
- Directly controlling external financial systems.
- Bypassing input validation, safety boundaries, or verification.
- Treating a plausible explanation as an observed fact when the data does not support it.

The agent can request an analytical action, but the action remains subject to the system's capability boundary, input validation, data-access restrictions, and verification responsibilities.

# 3. Agent Runtime Model

The conceptual runtime is:

```text
Understand
  -> Plan
  -> Act
  -> Observe
  -> Validate
  -> Update State
  -> Replan if necessary
  -> Verify
  -> Respond
```

This is an iterative control loop rather than a mandatory one-pass sequence. A task may return to planning or request understanding after an observation, failure, clarification, or verification result.

## 3.1 Understand

**Purpose:** Determine what the user is trying to learn or accomplish.

**Inputs:** Current user request, relevant conversation context, available data description, and validation findings.

**Expected output:** Interpreted intent, requested measures, entities, time scope, constraints, desired response, and any ambiguity or unsupported scope.

**Move forward when:** The agent has enough information to plan a supported analysis.

**Failure or branching behavior:** Ask a focused clarification question, explain that the request is unsupported, or report that the available data cannot answer it.

## 3.2 Plan

**Purpose:** Determine an appropriate sequence of analytical and reasoning steps.

**Inputs:** Interpreted request, available analytical capabilities, data requirements, current state, and known constraints.

**Expected output:** A provisional plan containing the next action or a sequence of actions, expected observations, and a verification need.

**Move forward when:** The next action has a clear purpose and sufficient inputs.

**Failure or branching behavior:** Simplify the plan, ask for missing information, or stop if no supported plan can answer the request.

## 3.3 Act

**Purpose:** Request execution of one selected analytical capability or another allowed action.

**Inputs:** Selected capability, scoped parameters, relevant data requirements, and execution context.

**Expected output:** An action result, status, evidence references, limitations, or an explicit failure.

**Move forward when:** The action returns a result that can be observed, including a valid empty or failed result.

**Failure or branching behavior:** Record the failure, consider recovery or replanning, and do not treat an uncompleted action as a successful result.

## 3.4 Observe

**Purpose:** Examine what the action actually produced rather than assuming it produced the expected result.

**Inputs:** Action status, output, evidence references, data-quality findings, and limitations.

**Expected output:** An observation describing what was learned, what remains unknown, and whether the result appears relevant to the request.

**Move forward when:** The result is sufficiently understood to validate and update state.

**Failure or branching behavior:** Mark the result incomplete, suspicious, empty, or inconsistent and return to planning or clarification as appropriate.

## 3.5 Validate

**Purpose:** Determine whether the action result and its structure are valid enough to continue.

**Inputs:** Action result, expected operation behavior, request scope, and required fields.

**Expected output:** A valid, qualified, invalid, incomplete, or failed status.

**Move forward when:** The result is structurally valid and its limitations are understood.

**Failure or branching behavior:** Replan, request missing information, isolate the invalid result, or stop safely.

## 3.6 Update State

**Purpose:** Record the request interpretation, plan progress, actions, observations, errors, assumptions, and verification status.

**Inputs:** Understanding, plan, action result, validation result, and current state.

**Expected output:** Updated execution state with completed and pending work clearly represented.

**Move forward when:** The updated state supports a next decision.

**Failure or branching behavior:** If state cannot be updated reliably, the agent should avoid presenting an untraceable result and should stop or return a bounded failure.

## 3.7 Replan if necessary

**Purpose:** Adapt when the original plan is insufficient, invalid, or changed by new information.

**Inputs:** Updated state, observations, failures, clarification, and verification findings.

**Expected output:** A revised plan, another action, a clarification request, a partial-result decision, or a safe termination.

**Move forward when:** The revised next step is justified by the observed state.

**Failure or branching behavior:** Avoid repeating an invalid action indefinitely; report inability to answer when recovery is not supported.

## 3.8 Verify

**Purpose:** Determine whether important calculations and interpretations are sufficiently supported before presentation.

**Inputs:** Candidate results, source evidence, request scope, and proposed interpretation.

**Expected output:** Passed, qualified, failed, or inconclusive verification with findings.

**Move forward when:** The final result is verified or explicitly qualified in a way that remains useful and non-misleading.

**Failure or branching behavior:** Reanalyze, narrow the conclusion, request more information, return a qualified partial result, or stop safely.

## 3.9 Respond

**Purpose:** Provide the user with a clear answer, clarification request, limitation, or safe failure.

**Inputs:** Verified or qualified results, evidence, scope, assumptions, relevant context, and response constraints.

**Expected output:** A grounded user-facing response.

**Move forward when:** The answer addresses the current request and does not require further action.

**Failure or branching behavior:** If a response cannot be grounded, the agent should state that it cannot answer reliably rather than fill the gap with speculation.

## 3.10 Iterative example

A request may follow this trajectory:

```text
User request
  -> Understand
  -> Plan
  -> Act
  -> Observe missing category information
  -> Replan
  -> Act with an available alternative grouping
  -> Observe
  -> Verify
  -> Respond with a qualified insight
```

The runtime should therefore represent what happened and why the next step was selected, not only the final text.

# 4. Request Understanding

The agent should conceptually transform a natural-language request into an analysis need. The interpretation should identify, where expressed or inferable from valid context:

- User intent.
- Requested analysis or measure.
- Relevant time period or periods.
- Relevant category, merchant, account, transaction type, or other dimension.
- Comparison requested.
- Desired level of detail.
- Constraints and exclusions.
- Information required to answer.
- Ambiguity or unresolved references.
- Whether the request is supported by the system and available data.

The agent should not assume that an apparent request for explanation authorizes unsupported causal claims. For example, "Why did I spend more?" may be interpreted as a request to identify evidence-supported drivers of the difference, not permission to claim the user's motive or circumstances.

## 4.1 Example: basic total

For "How much did I spend last month?", the agent should identify:

- A spending total is requested.
- The period is the previous calendar month or another period that must be clarified if context makes it ambiguous.
- Relevant spending records should be included according to available transaction-direction rules.
- Income, transfers, and refunds should not be silently included as spending when the data distinguishes them.
- The answer needs the total, period, inclusion scope, and material limitations.

## 4.2 Example: category question

For "What did I spend most on this month?", the agent should identify:

- A category-level spending aggregation is requested.
- The period is the current or referenced month.
- Transactions must be grouped by available or supported categories.
- Uncategorised or uncertain records may affect the ranking.
- The answer should include category totals and the basis or limitation of categorization.

## 4.3 Example: comparison and explanation

For "Why did I spend more in August?", the agent should conceptually identify:

- Spending in August must be calculated.
- An appropriate comparison period must be selected, such as the preceding comparable period, or clarified if context does not establish one.
- The difference must be calculated.
- Categories, merchants, and potentially noteworthy transactions may need to be compared to identify evidence-supported contributors.
- The explanation should describe observed drivers, not claim unsupported reasons for the user's behavior.

## 4.4 Example: unsupported question

For "Should I invest this money?", the agent should identify that the request is outside the initial spending-analysis scope and should decline or redirect without providing investment advice.

# 5. Context Construction

The agent should receive the relevant information needed for the current task rather than treating the entire transaction dataset as reasoning context for every step. Analytical capabilities should access and process the required transaction data through the system's data boundary.

## 5.1 User request

The current question or instruction is the immediate source of intent. It may contain explicit periods, categories, merchants, comparisons, constraints, and desired output. The agent should preserve the original request so the final response can be checked against what was asked.

## 5.2 Conversation context

Conversation context contains relevant prior exchanges, previous interpretations, and prior user clarifications needed for a follow-up. Irrelevant history should not be treated as an instruction or as evidence about the user's financial circumstances.

## 5.3 Transaction/data context

Transaction/data context describes the available dataset and the information relevant to the current task, such as date coverage, available fields, transaction direction, category availability, merchant identifiers, and known data-quality limitations. It may include references to records or computed subsets rather than the entire dataset.

## 5.4 Task context

Task context contains the current execution's plan, pending work, completed actions, assumptions, errors, clarification status, and response objective. It gives the agent a view of what has happened during the current run.

## 5.5 Analytical context

Analytical context contains results returned by previous actions, including calculations, groupings, comparisons, candidate patterns, evidence references, scope, status, and limitations. Results should remain connected to the action and data scope that produced them.

## 5.6 Verification context

Verification context contains checks performed on important results, the evidence inspected, the verification status, and any qualifications or failures. A result that has not been verified should not be represented as verified merely because it is present in analytical context.

The exact context-management mechanism, size, retention, and representation are TBD. Persistent memory is not assumed for the initial design.

# 6. Agent State

The agent should maintain conceptual state sufficient to make an execution inspectable and to support safe continuation or replanning. This is not an implementation schema.

| State Element | Purpose | Example |
|---|---|---|
| Original request | Preserve what the user asked | "Why did I spend more this month?" |
| Interpreted intent | Record the current understanding of the request | Compare spending and identify evidence-supported contributors |
| Constraints | Record scope and response limits | August versus July; spending only; no causal claims |
| Current plan | Describe intended next steps | Calculate both periods, compare categories, inspect contributors |
| Completed actions | Record actions already attempted | Period totals calculated; category grouping completed |
| Pending actions | Record work still required | Verify contributor explanation |
| Action results | Preserve outputs from capabilities | August total, July total, category differences |
| Observations | Record what results imply or fail to establish | Dining and travel account for most observed increase |
| Errors | Record action, data, or reasoning failures | Merchant grouping unavailable for some records |
| Assumptions | Make material interpretations visible | "Last month" interpreted as prior calendar month |
| Clarification status | Track whether user input is needed | Not required; period inferred from context |
| Verification status | Track result trust status | Period totals passed; causal interpretation not applicable |
| Final evidence | Identify support for the response | Period totals and top category differences |
| Response status | Track whether a response is ready or sent | Ready to respond |

State should distinguish an action that was planned from one that actually executed, and a result that was observed from one that was verified. This distinction helps prevent incomplete work from being presented as finished.

# 7. Planning

Planning means determining which supported analytical and reasoning steps are needed to answer the current request. It does not mean generating an unconstrained narrative about possible work, and it does not require a complex plan for every question.

## 7.1 When planning is needed

A simple request may need only a small plan. For example, "How much did I spend last month?" may require interpreting the period, selecting spending records, calculating a total, verifying it, and responding.

Planning becomes more important when:

- The request requires multiple analytical operations.
- One result determines the scope of a later operation.
- The user asks for a comparison and an explanation of the difference.
- The request refers to previous results.
- The data may be incomplete or ambiguous.
- Verification requires separate evidence or recomputation.

## 7.2 Planning sequence

For "Why did my spending increase last month?", a possible conceptual plan is:

1. Determine the relevant periods and spending inclusion rules.
2. Calculate spending for both periods.
3. Compare the totals.
4. Compare categories or other available dimensions.
5. Identify major contributors to the difference.
6. Investigate noteworthy transactions if the prior results do not sufficiently explain the change.
7. Verify the calculations and evidence-supported explanation.
8. Respond with the observed change, main contributors, and limitations.

This is a conceptual plan, not a fixed hard-coded workflow. The agent should stop early when the available evidence is sufficient and should add work only when the current results do not answer the question reliably.

## 7.3 Plan updates

The plan may change after an action. For example, if category data is missing, the agent may use merchant or transaction-description grouping if supported, ask the user for clarification, or report that a category explanation cannot be established. If verification fails, the agent should revise the plan rather than proceed as if verification succeeded.

# 8. Action and Tool Selection

An action or tool represents a request to an available analytical capability or allowed system operation. In the initial design, actions are analytical capabilities, not autonomous agents.

The agent should use an action when an operation is needed to answer the request and the operation is available within the system boundary. Potential capabilities include:

- Filtering transactions.
- Calculating totals or other aggregates.
- Grouping transactions.
- Category analysis.
- Period comparison.
- Merchant or contributor analysis.
- Recurring-pattern analysis.
- Unusual-activity analysis.

Not every capability is required for the MVP. The available capability set is TBD and will depend on data design and implementation scope.

## 8.1 Agent decision

The agent decides:

- Whether an action is needed.
- Which supported capability best matches the current analytical need.
- What scope and parameters the capability should receive.
- Whether actions must be sequential or can be treated independently.
- Whether an action result requires follow-up analysis or verification.

## 8.2 Action execution

The analytical capability executes the requested operation using validated data and explicit scope. It calculates, filters, groups, compares, or detects supported patterns. It returns structured conceptual results, status, limitations, and evidence references to the agent.

The agent should not assume that selecting an action means the action succeeded. It must observe the returned status and result before deciding what to do next.

## 8.3 Selection considerations

Selection should consider:

- Whether the capability directly addresses the interpreted intent.
- Whether its required fields are available.
- Whether its output can support the requested explanation.
- Whether the capability's limitations are acceptable.
- Whether a simpler action can answer the question.
- Whether the action is within the system and safety boundary.

# 9. Tool/Action Contract Principles

Each analytical action should ideally have:

- A clear purpose.
- Defined conceptual inputs.
- Defined conceptual outputs.
- Predictable behavior for valid inputs.
- Input-validation expectations.
- Explicit status and failure behavior.
- Scope and inclusion-rule information.
- Traceability to source transaction data or computed evidence.
- Uncertainty and limitation information where applicable.
- A clear indication of whether the result is complete, partial, empty, or failed.

Analytical capabilities should return structured results that the agent can reason over. This reduces the need for the agent to infer numerical values from prose and supports validation, verification, testing, and observability. The exact result schemas and execution mechanism are TBD.

An action should not silently perform additional analysis beyond its stated purpose. If additional work is required, it should be represented as another action or as a clearly documented part of a defined capability.

# 10. Execution and Observation

After selecting an action, the conceptual sequence is:

```text
Agent selects action
  -> Action executes
  -> Result returned
  -> Agent observes result
  -> Agent determines next step
```

The agent should inspect:

- Whether execution succeeded.
- Whether the required data was available.
- Whether the result has the expected information.
- Whether the result is complete or qualified.
- Whether the result addresses the intended question.
- Whether further analysis is needed.
- Whether the result is empty for a meaningful reason.
- Whether the result appears suspicious or inconsistent.
- Whether the result contains evidence references and relevant limitations.

Observation is more than receiving a value. It is the agent's assessment of what the action established, what it did not establish, and how that changes the current plan. An action that returns no matching transactions may be a valid empty result, not necessarily an execution failure. An action that returns a total without the requested period may be structurally incomplete even if the arithmetic is valid.

# 11. Validation and Verification

Validation and verification are related but distinct.

## 11.1 Validation

Validation determines whether an action or result is valid enough to continue processing. It focuses on input and execution integrity.

Examples include:

- Expected data exists.
- Required fields are present.
- Parameters match the supported capability.
- The result structure is valid.
- The computation completed successfully.
- The result status is understood.
- The result is not silently based on malformed values.

A validated result may still require verification before it is presented.

## 11.2 Verification

Verification determines whether an important result is sufficiently trustworthy and supported to present. It focuses on correctness, consistency, evidence, and interpretation.

Examples include:

- Numerical totals agree with the relevant source data.
- Comparison calculations are internally consistent.
- Period boundaries and inclusion rules match the request.
- Claimed contributors actually explain the observed difference.
- A category or recurring pattern is supported by the available evidence.
- The generated interpretation matches the analytical result.
- Unsupported causal claims have not been introduced.

Both are necessary because a result can be structurally valid but analytically wrong, or numerically correct but interpreted beyond what the evidence supports. The agent should use validation to decide whether it can continue and verification to decide whether an important conclusion can become part of the final response.

# 12. Replanning and Iteration

The agent should reconsider its current plan when:

- An action fails.
- Required data is insufficient.
- The result is empty.
- The result reveals an unexpected pattern.
- The result is inconsistent with an earlier observation.
- Verification fails.
- The original interpretation was incomplete.
- The user provides clarification that changes the task.
- A requested conclusion cannot be supported by the current evidence.

The agent should not blindly continue executing an invalid plan. It should update state and determine whether to:

- Retry an action when the failure may be transient or the inputs can be corrected.
- Modify the plan using an available alternative analysis.
- Perform another analysis to resolve an evidence gap.
- Ask the user a focused question.
- Return a partial result with explicit limitations.
- Terminate safely when no reliable path remains.

Replanning should be bounded and purposeful. Repeating the same unsuccessful action without new information does not constitute recovery.

# 13. Ambiguity and Clarification

The agent should avoid unnecessary clarification while preventing materially misleading analysis. It may infer a reasonable interpretation when the available context and data make that interpretation low-risk, but it should state a material assumption in the response.

For "How much did I spend recently?", possible ambiguity includes:

- What time period does "recently" mean?
- Does spending include transfers, refunds, or only outgoing purchases?
- Which transaction dataset or account scope should be used?
- Is the user asking for a total or a comparison?

The agent should:

- **Infer a reasonable interpretation** when the project context or conversation establishes it and the result is unlikely to be materially misleading.
- **State an assumption** when an inferred interpretation materially affects the result but remains reasonable to use.
- **Ask a clarification question** when competing interpretations would materially change the answer and cannot be resolved from context.
- **Refuse to proceed** when the request is unsupported, prohibited, or cannot be answered safely from available data.

Clarification questions should be focused and should request only the missing information needed to proceed. The exact ambiguity policies are TBD and should be evaluated against supported use cases.

# 14. Failure Handling

The agent should fail safely rather than fabricate an answer.

| Failure mode | Desired conceptual behavior |
|---|---|
| Invalid request | Identify what is malformed or unusable and ask for a correction or provide a bounded failure response. |
| Unsupported request | Explain that the request is outside the supported spending-analysis scope and do not answer an unsupported financial question. |
| Missing data | Identify the missing field, period, or source information and ask for it when the user can provide it; otherwise state the limitation. |
| Malformed data | Prevent affected records from silently entering analysis; report the impact and continue only if the remaining result is not misleading. |
| Failed analytical action | Record the failure, consider a justified retry or alternative plan, and do not treat the action as successful. |
| Empty analytical result | Distinguish no matching records from failed execution and explain what the empty result means for the request. |
| Inconsistent result | Flag the inconsistency, avoid presenting it as reliable, and reanalyze or terminate safely. |
| Verification failure | Do not present the result as verified; revise, qualify, ask for more information, or report inability to answer. |
| Reasoning failure | Return a bounded clarification or inability-to-answer response rather than inventing intent, facts, or calculations. |
| Unexpected system failure | Stop safely, preserve appropriate diagnostic state, avoid unnecessary sensitive disclosure, and report that the task could not be completed. |

A partial answer is acceptable only when the verified portion is useful on its own and the uncompleted portion is clearly identified.

# 15. Grounded Interpretation

The agent converts analytical results into insights by keeping three kinds of statements distinct.

## 15.1 Observed fact

An observed fact is directly supported by transaction data or deterministic analysis.

Example:

> Dining spending increased by 4,200 compared with the previous month.

This statement should be supported by the relevant period totals or category comparison.

## 15.2 Interpretation

An interpretation is a reasonable explanation derived from observed evidence and expressed with an appropriate level of confidence.

Example:

> The increase was primarily driven by several higher-value dining transactions.

This is acceptable when the contributor analysis identifies those transactions and the response makes clear that it describes the observed drivers rather than the user's motive.

## 15.3 Unsupported assumption

An unsupported assumption is a claim not established by the available evidence.

Example:

> You spent more because you were stressed.

The agent must not present this as fact because transaction data generally cannot establish the user's emotional state or cause of spending.

The agent may provide evidence-supported interpretations, but it should qualify uncertainty, identify the evidence, and avoid converting correlation or temporal coincidence into causation. A numerically correct result does not automatically justify every explanation that could be associated with it.

# 16. Response Generation

The final response should:

- Directly answer the user's question.
- Present relevant numerical evidence.
- State the period, filters, categories, merchants, and other material scope.
- Explain important conclusions using verified analytical results.
- Distinguish observed facts from interpretation.
- Communicate uncertainty and limitations when they matter.
- Avoid unnecessary technical details about internal execution.
- Avoid unsupported financial, causal, or personal claims.

Depending on the request and result, the response may include:

- Totals and period comparisons.
- Percentage or absolute changes when calculated and relevant.
- Contributing categories, merchants, or transactions.
- Examples of transactions supporting a pattern.
- Assumptions about terms such as "last month" or "recently".
- Missing-data and categorization limitations.
- A clarification question.
- A safe explanation that the request cannot be answered.

The agent should not use a fixed response template as an architectural requirement. Response structure should remain adaptable to the request while preserving evidence, scope, and uncertainty requirements. A specific prompt or response-generation mechanism is TBD.

# 17. Conversation and Follow-Up Questions

The agent should support bounded follow-up questions when prior analytical context remains relevant.

Example:

```text
User: Why did my spending increase in August?
Agent: [Provides a comparison and evidence-supported contributors]
User: What about restaurants specifically?
```

For the second question, the agent should recognize that the period and the prior spending comparison may remain relevant, while the category or merchant scope is being narrowed to restaurants. It should reuse valid context, perform only the additional analysis required, and state any changed scope.

Conceptually retained information may include:

- The prior request and interpreted intent.
- The periods and filters used.
- Previous analytical results and evidence references.
- Assumptions and limitations.
- Which results were verified.
- References such as "that increase" or "those transactions" when they can be resolved unambiguously.

The agent should ask for clarification when a follow-up reference could refer to multiple prior results. It should not infer unspoken personal circumstances from the conversation.

The design distinguishes:

- **Current execution state:** State for the active task or action sequence.
- **Conversational context:** Relevant information carried between turns in a supported session.
- **Persistent memory:** Information retained beyond a session. This is not assumed for the initial design and remains TBD.

# 18. Agent Decision Policy

The agent should follow these high-level principles when deciding what to do next:

- Prefer a direct answer when sufficient verified evidence already exists.
- Use deterministic analytical capabilities for numerical operations.
- Choose the simplest supported action that can answer the current need.
- Avoid unnecessary actions and unnecessary exposure of transaction data.
- Gather additional evidence when the current result does not support the requested conclusion.
- Verify important results before presenting them.
- Ask for clarification when ambiguity materially affects correctness.
- State material assumptions when a reasonable inference is used.
- Do not fabricate missing information, results, or evidence.
- Treat failures and empty results according to their actual status.
- Replan when the current plan is invalid or insufficient.
- Respect financial safety and data-access boundaries.
- Stop when the question has been adequately answered.
- Do not continue acting after the task is complete.
- Prefer a qualified partial result or safe inability-to-answer response over unsupported certainty.

These are behavioral principles, not code or a finalized policy engine.

# 19. Example Agent Trajectories

These examples are conceptual trajectories, not implementation traces.

## Example 1 - Simple question

**Request:** "How much did I spend last month?"

1. **Understand:** Identify a spending total and interpret "last month" using available context.
2. **Plan:** Select a spending-total analysis followed by verification.
3. **Action:** Request the relevant period's spending total.
4. **Observe:** Receive the total, included records, scope, and limitations.
5. **Validate:** Confirm that the result contains the required period and status.
6. **Verify:** Check the total against the relevant transaction evidence and inclusion rules.
7. **Respond:** State the total, period, what was included, and any material limitation.

## Example 2 - Multi-step analysis

**Request:** "Why did I spend more this month than last month?"

1. **Understand:** Identify a comparison and a request for evidence-supported drivers.
2. **Plan:** Calculate both period totals, compare categories, identify contributors, and verify.
3. **Action:** Request totals for both comparable periods.
4. **Observe:** Confirm that the current period is higher and record the difference.
5. **Action:** Request category comparison for the same periods.
6. **Observe:** Identify categories with the largest increases and note uncategorized records.
7. **Action:** Request contributor or transaction-level analysis for the main increases.
8. **Observe:** Identify transactions supporting the observed difference.
9. **Validate:** Check that all actions used the same periods and spending scope.
10. **Verify:** Recheck totals and whether identified contributors account for the reported difference.
11. **Respond:** Explain the observed increase and main evidence-supported contributors, without claiming why the user made those purchases.

## Example 3 - Ambiguous request

**Request:** "How much did I spend recently?"

1. **Understand:** Identify a spending total but unresolved meaning for "recently" and possibly the data scope.
2. **Plan:** Determine whether conversation context establishes a period.
3. **Observe:** No reliable period is available.
4. **Replan:** Do not select an arbitrary period that could mislead the user.
5. **Respond:** Ask a focused question such as, "Which period should I use: the last 7 days, the current month, or another range?"

## Example 4 - Verification failure

**Request:** "Did my grocery spending increase?"

1. **Understand:** Identify a comparison between two relevant periods.
2. **Plan:** Calculate comparable grocery totals and verify them.
3. **Action:** Receive a result, but the period filters differ between the two totals.
4. **Observe:** The result is not comparable.
5. **Validate:** Mark the result invalid for the requested comparison.
6. **Replan:** Re-run the comparison with consistent periods if the data supports it.
7. **Observe:** The required source information is incomplete and the mismatch cannot be resolved.
8. **Verify:** Verification fails because the comparison cannot be supported.
9. **Respond:** Explain that the available data cannot reliably establish the comparison and identify the limitation, rather than presenting the initial result.

## Example 5 - Follow-up question

**First request:** "Why did my spending increase in August?"

1. Understand and analyze August versus the established comparison period.
2. Verify the total difference and identify evidence-supported contributors.
3. Respond with the observed change and relevant categories or transactions.

**Follow-up:** "What about restaurants specifically?"

1. **Understand:** Resolve the follow-up against the previous periods and narrow the dimension to restaurants.
2. **Plan:** Filter the same comparable periods to restaurant-related records and compare them.
3. **Act and observe:** Receive restaurant totals and supporting records.
4. **Verify:** Check that the restaurant scope and periods are consistent.
5. **Respond:** Answer the narrowed question and state if categorization or merchant matching is uncertain.

# 20. Agent Architecture Options

## Option A - Single-step response

A single-step response would interpret the request and produce an answer without an explicit action and observation loop. It has low apparent complexity and may be adequate for simple conversational tasks, but it provides weak control over deterministic calculations, verification, failure recovery, and multi-step analysis.

## Option B - Fixed analytical pipeline

A fixed pipeline would execute a predefined sequence of analyses for every request. It can be predictable and testable, but it may perform unnecessary work and may not adapt well to different questions, follow-ups, missing data, or intermediate results.

## Option C - Single agent with analytical capabilities

A single agent interprets the request, plans and selects actions, observes results, replans when necessary, and coordinates deterministic analytical capabilities. This supports context-dependent requests while keeping calculations and verification in explicit responsibilities. It has more behavioral complexity than a fixed pipeline, but the runtime and state can be inspected and tested.

## Option D - Multi-agent system

A multi-agent system could divide responsibilities among specialized agents. It may become useful for a larger future scope, but it introduces additional coordination, state, testing, and failure complexity without an established MVP requirement.

| Option | Flexibility | Correctness | Complexity | Testability | Extensibility | Suitability now |
|---|---|---|---|---|---|---|
| Single-step response | Low to medium | Weak for calculations and verification | Low | Limited | Limited | Low |
| Fixed analytical pipeline | Medium | Strong for fixed operations | Low to medium | Strong for known flows | Medium | Possible for narrow subsets |
| Single agent plus analytical capabilities | High within supported scope | Strong when calculations and verification are separated | Medium | Strong if state and actions are explicit | High | Preferred |
| Multi-agent system | Potentially high | Depends on coordination | High | More difficult | Potentially high | Not justified for MVP |

The current project should begin with **a single agent plus deterministic analytical capabilities/tools**. Multi-agent architecture may be reconsidered only if future requirements and evaluation demonstrate that one agent is insufficient.

# 21. Agent Evaluation Considerations

The agent should eventually be evaluated on:

- Understanding the analytical intent of supported requests.
- Resolving periods, dimensions, constraints, and follow-up references appropriately.
- Selecting suitable analytical capabilities.
- Avoiding unnecessary or unsupported actions.
- Producing reasonable plans for multi-step requests.
- Executing the required sequence and using returned observations.
- Recovering appropriately from failed, empty, or inconsistent actions.
- Requesting clarification when ambiguity materially affects correctness.
- Verifying important results before responding.
- Keeping interpretations grounded in analytical evidence.
- Avoiding fabricated transaction facts and numerical results.
- Returning relevant and understandable responses.
- Maintaining valid conversational continuity.
- Respecting safety and data-access boundaries.
- Stopping when the task is complete.

Detailed evaluation datasets, test cases, metrics, thresholds, and comparison methods belong to the later testing and evaluation phase. No quantitative evaluation target is defined here.

# 22. Agent Observability Requirements

The agent execution should eventually make the following information observable for debugging and evaluation:

- Original request.
- Interpreted intent and scope.
- Relevant context used.
- Current plan and plan updates.
- Selected action or analytical capability.
- Action inputs at an appropriate level of detail.
- Action status and result metadata.
- Observations made from each result.
- State transitions.
- Validation outcomes.
- Verification request and result.
- Replanning and recovery decisions.
- Clarification requests.
- Errors and failure categories.
- Final response status and response evidence.

Observability should make the execution understandable without unnecessarily exposing raw transaction data or sensitive personal information. The event format, retention behavior, and tracing or logging implementation are TBD.

# 23. Agent Security and Safety Boundaries

The agent must:

- Operate only within the approved personal transaction and spending-analysis scope.
- Use only transaction data and context made available within the authorized system boundary.
- Never execute financial transactions or control money movement.
- Never modify financial accounts or financial records as an external action.
- Never fabricate financial information, numerical results, evidence, or capabilities.
- Avoid investment, tax, credit, banking, payment, and financial-product advice or action.
- Respect validation, data-access, and verification boundaries.
- Avoid exposing unnecessary sensitive financial information in responses or observable execution data.
- Communicate uncertainty and material limitations.
- Avoid unsupported claims about why the user spent money.
- Apply the same boundaries to follow-up questions and contextual requests.

These are agent-level safety constraints. Production authentication, authorization, encryption, hosting, retention, and other security implementation are outside this document and remain TBD.

# 24. Initial Agent Design Decision

The initial agent should be:

- A single agent.
- Focused on personal spending and transaction analysis.
- Capable of interpreting supported natural-language requests.
- Capable of selecting appropriate analytical capabilities.
- Capable of iterative execution rather than only a single-step response.
- Capable of observing action results.
- Capable of validation and verification.
- Capable of replanning when necessary.
- Capable of grounded response generation.
- Reliant on deterministic analytical capabilities for appropriate numerical operations.
- Simple and inspectable enough to test and evaluate.

The agent is a coordinator and interpreter. It does not become a replacement for analytical capabilities, the verification responsibility, or system-level safety boundaries.

# 25. Design Decisions and Rationale

| Decision | Rationale | Status |
|---|---|---|
| Start with one agent | The MVP needs one decision-making component, and multiple agents would add coordination complexity without an established requirement. | Decided |
| Separate agent reasoning from deterministic analysis | The agent is suited to intent, planning, and interpretation; analytical capabilities are better suited to repeatable numerical work. | Decided |
| Use an iterative runtime | Requests may require multiple actions, observations, clarification, recovery, and replanning before a reliable answer is possible. | Decided |
| Maintain explicit execution state | State makes progress, failures, evidence, and verification status inspectable and supports safe continuation. | Decided |
| Treat verification as a first-class step | Important numerical results and interpretations must be checked before being presented. | Decided |
| Require grounded interpretation | The agent should distinguish observed facts, evidence-supported interpretations, and unsupported assumptions. | Decided |
| Support clarification and replanning | Ambiguous requests and incomplete analyses cannot always be resolved by the initial plan. | Decided |
| Keep action contracts conceptually explicit | Clear purpose, inputs, outputs, status, limitations, and traceability improve testability and agent decisions. | Decided |
| Avoid unnecessary actions | The agent should use the simplest sufficient analysis and stop when the question is answered. | Decided |
| Defer persistent memory | The requirements establish bounded context but do not require long-term memory for the MVP. | Decided for MVP; future need TBD |
| Defer exact planning and recovery implementation | The behavior is defined conceptually, while the mechanism belongs to implementation design. | Implemented deterministically in `runtime/planning.py` and `runtime/replanning.py`; recovery is explicit error recording and status propagation. |
| Defer model, prompts, state schemas, and action schemas | These are implementation choices not established by current requirements. | State schemas (`runtime/state.py`) and action schemas (`Action` dataclass, tool registry in `runtime/tools.py`) are now concrete; model and prompts remain TBD. |
| Reconsider multiple agents only if justified later | Additional agents should be introduced only if future requirements and evaluation show that one agent is insufficient. | Future option; not MVP |

# 26. Open Questions / TBD

The following agent-design questions remain unresolved:
- **Model/provider:** Qwen3 1.7B via Ollama is the provisional MVP model (DEC-021, DEC-023). Provider-neutral `LLMClient` boundary preserved.
- **LLM-driven loop:** Implemented in `runtime/llm_loop.py` (DEC-023, provisional/experimental): bounded loop with `LLMLoopConfig` (max_model_steps=6, max_tool_calls=4, max_consecutive_repeats=2, retry_invalid=1), `LLMTerminationReason`, `ToolCallValidation`, `build_llm_request`, `summarise_observation_for_llm`, `validate_llm_tool_call`, `grounding_gate`, and `run_llm_loop`. Invalid proposals (malformed output or failed tool-call validation) retry within the same step via an inner retry loop; `FakeLLMClient`-raised malformed output is retryable, other `LLMError` subclasses terminate as `model_error` (a `ResponseSequenceExhaustedError` arriving mid-retry terminates as `max_retries_invalid`). Model period arguments (`YYYY-MM` strings, `(year, month)` pairs) are coerced to `Period` objects before execution, with booleans rejected (`True`/`False` are `int` subclasses and must not be treated as `1`/`0`). Deterministic `run()` remains unchanged and default.
- **Reversed periods (DEC-023):** `period_comparison` with `period_a > period_b` is REJECTED deterministically at semantic validation (not normalized); order is semantically meaningful (`absolute_difference = total_b - total_a`). The model receives an explicit invalid-proposal error and may retry with corrected order.
- **Hybrid pending-actions (DEC-023):** after each validated model tool call, the first pending action with the same tool name is consumed (by name) to avoid duplicate planned evidence; remaining unproposed planned actions are gap-filled deterministically through the same execute -> observe -> verify path with budget checks. Gap-fill does not bypass verification and cannot execute invalid actions (the plan is deterministic, never model input).
- **Grounding gate:** MVP deterministic gating layer checks currency-anchored monetary figures (e.g. "USD 400.00"; bare years/counts are not claims) in final-response drafts against verified observations. Not a semantic claim verifier: a correct number with a wrong qualitative explanation may still pass.
- **Clarification:** Unsupported/ambiguous requests may terminate with clarification response and no tool execution. Architecture extensible for future multi-turn clarification; not implemented now.
- Which exact model or reasoning mechanism, if any, will support request understanding and interpretation?
- What model interaction strategy will be used?
- What prompt architecture, if any, is appropriate?
- ~~What exact representation will be used for agent execution state?~~ Implemented: `runtime/state.py` defines `AgentState` as a mutable dataclass with explicit fields for request, intent, plan, pending/completed actions, observations, verification records, errors, assumptions, trajectory, and response.
- How will context be selected and bounded within the available reasoning context?
- ~~What conceptual or concrete action schemas will analytical capabilities use?~~ Implemented: `Action` dataclass (`name`, `params`, `purpose`) and tool registry in `runtime/tools.py`.
- ~~How will actions be executed and their statuses returned?~~ Implemented: `execute_tool(name, params)` dispatches to the matching analytical capability; results recorded as `Observation` dataclasses.
- ~~How will planning be implemented for simple and multi-step requests?~~ Implemented: `runtime/planning.py` maps intents to structured action sequences; multi-step for spending-change explanation.
- ~~How will replanning be implemented after failures or new observations?~~ Implemented: `runtime/replanning.py` performs bounded follow-up decisions after observing results.
- What memory implementation, if any, is required?
- How much conversation persistence is required beyond the current session?
- ~~How will important analytical results be verified in implementation?~~ Implemented: `runtime/checks.py` wires tool results to `verification.py` and classifies trust (verified/failed/inconclusive/unverified).
- What retry and error-recovery strategy is appropriate?
- What evaluation dataset will test agent behavior?
- **Invalid-output policy:** One bounded retry; second consecutive invalid model output terminates safely.
- What evaluation metrics and test thresholds should be defined later?
- What observability implementation and retention policy are appropriate?
- What privacy controls are required for prompts, context, action inputs, and observable state?
- Which analytical capabilities and pattern definitions belong in the MVP?
- How should ambiguous terms such as "recently" be handled for the supported use cases?
- **Termination reasons:** `LLMTerminationReason` enum: `budget_steps`, `budget_tool_calls`, `max_consecutive_repeats`, `model_error`, `max_retries_invalid`, `grounding_fallback`, `response_complete`, `unsupported`, `ambiguous`.

These questions remain TBD and should be resolved through data design, implementation, testing, and evaluation rather than by assuming a specific framework, provider, storage mechanism, or architecture.

# 27. Handoff to Next Phase

This document defines the conceptual behavior and runtime of the Personal Finance Agent: its responsibilities, boundaries, state and context, planning, action selection, execution, observation, validation, verification, replanning, failure handling, grounded interpretation, response generation, safety constraints, and evaluation considerations.

The next document should be `docs/05_data_design.md`. It should define the transaction-data model and data lifecycle required by the system and agent, including:

- Transaction schema.
- Data sources.
- Input formats.
- Normalization.
- Validation.
- Categorization.
- Data quality.
- Derived analytical fields.
- Synthetic and real data strategy.
- Storage considerations.
- Traceability.
- Privacy considerations.
- Data flow into analytical capabilities.

The data design should support the established agent and system architecture rather than independently introducing new architecture or technology choices.
