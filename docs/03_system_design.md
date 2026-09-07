# 1. System Design Overview

This document defines the high-level system design for the Personal Finance Agent. It translates the problem, objectives, and scope in `docs/01_problem_and_objectives.md` and the requirements in `docs/02_requirements.md` into conceptual system boundaries, logical components, responsibilities, interfaces, data flow, and architectural principles.

The design establishes what responsibilities must exist in the system and how they relate. It does not define application code, deployment infrastructure, framework choices, data schemas, model providers, prompts, or detailed agent behavior.

## Decided at this stage

- The system is an analysis and insight system for personal transaction and spending data.
- The system receives a user request and relevant transaction data, validates them, determines the required analysis, performs appropriate analytical operations, verifies important results, and returns a grounded response.
- The architecture separates request interaction, validation, reasoning, deterministic analysis, data access, verification, response generation, and observability as logical responsibilities.
- Deterministic computation should be used for arithmetic, filtering, aggregation, comparison, and similar operations where appropriate.
- Intelligent reasoning may be used for request understanding, flexible task interpretation, ambiguity handling, planning, and contextual explanation.
- Verification is a first-class responsibility separate from response generation.
- The initial system should favor a simple modular application rather than distributed infrastructure or multiple agents.
- The system must not execute payments, move money, provide investment or tax advice, make credit decisions, or recommend financial products.

## Deferred/TBD

- The exact agent architecture, runtime state representation, planning mechanism, and action or tool contracts.
- The supported transaction schema, input formats, data source, and categorization approach.
- The interaction interface and deployment environment.
- The model or reasoning mechanism, if any, used for language understanding or interpretation.
- Persistent storage and long-term conversational memory.
- Observability, security, privacy, and performance implementation details.
- Whether external APIs, additional specialized components, or additional agents are justified in a future version.

# 2. Design Goals

## 2.1 Correctness

The system should produce numerical and analytical results that correspond to the relevant transaction data, filters, periods, and inclusion rules. Incorrect totals or comparisons would directly undermine the purpose of helping users understand their spending.

## 2.2 Grounded analysis

Important conclusions should be connected to transaction records, computations, or other available evidence. The system should preserve the distinction between what the data shows and what might merely be an interpretation.

## 2.3 Verification

Important results should have a verification path before they are presented. Verification reduces the risk that an incorrect calculation, incomplete analysis, or unsupported interpretation becomes a user-facing claim.

## 2.4 Separation of deterministic computation and intelligent reasoning

The design should give arithmetic, filtering, grouping, aggregation, and comparison to deterministic analytical capabilities where appropriate. Reasoning should add value for language understanding, flexible request interpretation, planning, ambiguity handling, and explanation rather than replacing reliable computation without justification.

## 2.5 Testability

Logical responsibilities and boundaries should be clear enough that input handling, analytical calculations, agent decisions, verification, safety boundaries, and response behavior can be tested independently and together.

## 2.6 Observability

The system should eventually expose enough information to understand what happened during an execution: what request was received, what decisions were made, which analyses ran, what they returned, what was verified, and where errors occurred. This is necessary for debugging and evaluation of an agentic system.

## 2.7 Maintainability

The initial design should avoid coupling user interaction, analysis, reasoning, and response generation into one opaque responsibility. Clear logical boundaries should make it possible to change one area without unnecessary changes elsewhere.

## 2.8 Extensibility

The design should leave clean boundaries for additional transaction formats, analytical capabilities, richer interfaces, persistent storage, external data sources, and more complex workflows if later requirements justify them. Extensibility must not require implementing those capabilities now.

## 2.9 Simplicity for the initial version

The first version should contain only the responsibilities needed to demonstrate the core agentic analysis loop. Logical components do not imply separate processes, services, databases, or infrastructure.

## 2.10 Controlled ambiguity and error handling

The system should avoid silently guessing when a request or record is materially ambiguous. It should clarify, narrow the answer, return a qualified partial result, or stop safely depending on the situation.

# 3. System Boundary

## 3.1 Inside the system

The system includes the logical responsibilities required to:

- Receive a user request and relevant transaction data within the supported scope.
- Validate request and transaction-data inputs.
- Determine the user's analytical intent and relevant context.
- Select and sequence the analytical operations needed for a request.
- Provide transaction data to analytical operations.
- Execute deterministic spending analyses such as filtering, aggregation, grouping, period comparison, contributor analysis, recurring-pattern analysis, and potentially noteworthy-activity analysis where supported.
- Observe analytical results and their limitations.
- Verify important calculations and conclusions against available evidence.
- Interpret verified results in relation to the user's request.
- Generate a clear, grounded response that includes relevant numerical evidence, scope, assumptions, and limitations.
- Handle ambiguity, unsupported requests, failures, and verification problems.
- Capture conceptual execution and observability information.

These are logical responsibilities. They may initially be implemented within one application or process.

## 3.2 Outside the system

The system boundary excludes:

- Banking infrastructure and automated banking transactions.
- Payment execution or movement of money.
- Investment management or investment advice.
- Tax filing or tax advisory systems.
- Loan or credit decision systems.
- Financial-product recommendation systems.
- Replacement of professional financial advisors.
- External financial data access unless a later requirement explicitly establishes it.
- Production-scale identity, access, hosting, and operational infrastructure beyond the needs of the selected prototype.

The system analyzes transaction data supplied within its authorized scope. It should not imply access to financial information or services that are not actually available to it.

# 4. Architectural Principles

## 4.1 Separation of concerns

Request handling, input validation, request understanding, decision-making, analysis, data access, verification, response generation, and observability should be separate logical responsibilities. This separation supports testing, traceability, and future change.

## 4.2 Deterministic computation

Arithmetic, filtering, aggregation, period comparison, and other computations with a well-defined result should be performed by conventional deterministic analytical capabilities where appropriate. The reasoning layer should not be the source of truth for numerical calculations when a direct calculation is available.

## 4.3 Intelligent reasoning where useful

Natural-language understanding, flexible task interpretation, planning, contextual follow-up, ambiguity handling, and explanation may use intelligent reasoning where it provides value. The design does not require every part of the system to use reasoning.

## 4.4 Evidence-grounded outputs

Response generation should consume analytical results and their supporting evidence rather than independently inventing facts. Important outputs should remain traceable to the data and computations that support them.

## 4.5 Verification before response

Important numerical and analytical outputs should pass through a verification responsibility before they become final user-facing claims. A response should be qualified, revised, or withheld when verification fails.

## 4.6 Explicit state

The system should represent enough request, execution, action, observation, verification, and error state to make the current status and history of an analysis understandable. The exact representation belongs to Agent Design.

## 4.7 Extensible boundaries

Logical components should communicate through conceptual contracts rather than relying on hidden assumptions about each other's internals. New capabilities should be addable at existing boundaries where possible.

## 4.8 Observability by design

Important requests, decisions, actions, results, verification outcomes, errors, and final responses should be identifiable as events or stages of an execution. The implementation of logging or tracing remains TBD.

## 4.9 Minimal initial architecture

The design should not introduce distributed deployment, persistent storage, external services, multiple agents, or other infrastructure without a current requirement. A logical boundary is valuable even when several responsibilities initially share one application or process.

# 5. High-Level Architecture

The initial conceptual architecture consists of the following logical components:

1. **User Interaction / Request Boundary** receives requests and returns responses.
2. **Input Validation** checks request and transaction-data validity and completeness.
3. **Request Understanding / Agent** determines intent, context, scope, and the next required action.
4. **Analysis Orchestration** coordinates the selected analytical operations and their results.
5. **Deterministic Analysis Capabilities** perform supported financial calculations and pattern analyses.
6. **Transaction/Data Access** provides the relevant transaction data to authorized analytical operations.
7. **Result Validation / Verification** checks calculations, evidence, consistency, and interpretation support.
8. **Response Generation** transforms verified results into a clear, grounded response.
9. **Observability** captures enough execution information to understand system behavior.

These are logical components, not required deployed services. In the initial prototype, several or all of them may live within one application or process. The architecture separates the responsibilities conceptually so that they can be tested and evolved independently without prematurely selecting a physical deployment model.

At a high level:

```text
User
  -> Request Boundary
  -> Input Validation
  -> Request Understanding / Agent
  -> Analysis Orchestration
  -> Data Access
  -> Deterministic Analysis Capabilities
  -> Result Validation / Verification
  -> Response Generation
  -> Request Boundary
  -> User
```

Observability surrounds these stages and records material events, decisions, results, failures, and verification status.

# 6. Component Responsibilities

## 6.1 User Interaction / Request Boundary

**Purpose:** Provide the boundary through which a user submits a request and receives a response.

**Responsibilities:**

- Receive a user request and any transaction-data input within the supported interaction scope.
- Pass the request and data to validation.
- Return a final response, clarification request, limitation, or safe failure message.
- Preserve the distinction between user-visible content and internal execution information.

**Inputs:** User request, transaction-data input, and relevant prior context when supported.

**Outputs:** A user-facing response, clarification request, or bounded error/limitation message.

**Should not be responsible for:** Financial calculations, deciding the analytical plan, categorizing transactions, independently interpreting unsupported causes, or performing financial actions.

**Dependencies:** Input Validation, Response Generation, and the context needed for a supported conversation.

## 6.2 Input Validation

**Purpose:** Determine whether request and transaction-data inputs are sufficiently valid for the requested work.

**Responsibilities:**

- Check that required request information is present or identify ambiguity.
- Check that transaction data can be interpreted within the supported input scope.
- Detect malformed dates, amounts, formats, missing required values, and other material data-quality problems.
- Identify limitations that should be carried into analysis and response generation.
- Reject, isolate, or qualify unusable input rather than silently passing it through.

**Inputs:** User request, transaction data, and the currently supported input expectations.

**Outputs:** Validated input, validation findings, identified limitations, or a request for clarification/correction.

**Should not be responsible for:** Deciding the full analytical plan, performing user-facing interpretation, or selecting an implementation technology.

**Dependencies:** Request Boundary, Data Access or data representation, and Request Understanding when validation depends on request scope.

## 6.3 Request Understanding

**Purpose:** Determine what the user is asking to understand and which scope is relevant.

**Responsibilities:**

- Identify analytical intent, measures, entities, periods, filters, and desired output.
- Resolve references to prior context when supported.
- Identify ambiguity, unsupported requests, prohibited requests, and missing scope.
- Translate a natural-language request into a structured conceptual analysis need.

**Inputs:** Validated user request, relevant conversation context, and available data description.

**Outputs:** Interpreted request, scope, constraints, ambiguity findings, or a clarification/unsupported-request result.

**Should not be responsible for:** Performing arithmetic, directly changing transaction data, or claiming conclusions before analysis and verification.

**Dependencies:** Input Validation, conversation context, Agent / Decision Layer, and available data metadata.

## 6.4 Agent / Decision Layer

**Purpose:** Determine what should happen next based on the interpreted request and current execution state.

**Responsibilities:**

- Decide whether to request clarification, select an analysis, continue an existing task, recover from failure, or respond with a limitation.
- Determine the necessary sequence for multi-step requests.
- Select an appropriate analytical capability through an abstract capability boundary.
- Track observations, intermediate results, verification status, and relevant state.
- Decide when the task has enough verified information for response generation.

**Inputs:** Interpreted request, available capabilities, current execution state, analytical observations, and verification findings.

**Outputs:** A next action, analysis plan, clarification request, recovery decision, or response-generation request.

**Should not be responsible for:** Replacing deterministic calculations, inventing evidence, directly executing financial actions, or bypassing verification for important results.

**Dependencies:** Request Understanding, Analysis Orchestration, Analysis Capabilities, Verification, Context/State, and Observability.

Detailed agent architecture is deferred to `docs/04_agent_design.md`.

## 6.5 Analysis Orchestration

**Purpose:** Coordinate the execution of one or more selected analytical capabilities without taking over request interpretation or numerical calculation.

**Responsibilities:**

- Receive an analysis plan or next action from the Agent / Decision Layer.
- Prepare the scoped inputs required by each selected capability.
- Invoke the required analytical operations in the requested sequence.
- Return intermediate results, statuses, errors, and evidence references to the agent.
- Preserve the relationship between multi-step operations and their intermediate results.

**Inputs:** Agent decision, analysis plan, validated scope, and data requirements for the selected capabilities.

**Outputs:** Ordered analytical observations, operation status, failures, and references needed for verification.

**Should not be responsible for:** Interpreting user intent, inventing analytical results, independently changing the analysis plan, generating the final response, or bypassing verification.

**Dependencies:** Agent / Decision Layer, Analysis Capabilities, Data Access / Transaction Data Layer, Verification, and Observability.

## 6.6 Analysis Capabilities

**Purpose:** Perform supported transaction and spending analyses with defined analytical behavior.

**Responsibilities:**

- Filter transactions by supported dimensions.
- Calculate totals and other numerical aggregates.
- Group transactions by categories, merchants, periods, or other supported dimensions.
- Compare time periods using stated inclusion rules.
- Identify contributors to spending.
- Identify candidate recurring patterns.
- Identify potentially unusual or noteworthy activity where a comparison basis exists.
- Return intermediate and final analytical results with scope, evidence references, and limitations.

**Inputs:** Analysis request, validated scope, transaction data, and relevant configuration or assumptions.

**Outputs:** Deterministic analytical results, intermediate observations, evidence references, status, and limitations.

**Should not be responsible for:** Interpreting user motives, generating unsupported causal explanations, selecting the user's next action, or presenting unverified conclusions directly to the user.

**Dependencies:** Data Access / Transaction Data Layer, Analysis Orchestration, and Verification.

## 6.7 Data Access / Transaction Data Layer

**Purpose:** Provide relevant transaction data to authorized analysis responsibilities.

**Responsibilities:**

- Make the supplied transaction data available within the supported scope.
- Apply requested data selection or retrieval boundaries.
- Preserve source identity and traceability where available.
- Report missing, unavailable, or inconsistent data.
- Limit access to the information needed for a particular analytical operation where practical.

**Inputs:** Transaction-data input and a scoped data request.

**Outputs:** Relevant transaction records, data metadata, source references, and data-quality limitations.

**Should not be responsible for:** Understanding natural-language intent, deciding the analysis, interpreting financial behavior, or persisting data by default.

**Dependencies:** Input Validation, Analysis Capabilities, Security/Privacy boundaries, and any future storage or source mechanism selected during data design.

## 6.8 Verification

**Purpose:** Check whether important results and conclusions are supported before they are presented.

**Responsibilities:**

- Recheck important calculations against the relevant transaction data.
- Check that filters, periods, grouping, and inclusion rules match the request.
- Check consistency between intermediate and final results.
- Check that interpretations are supported by the analytical evidence.
- Identify missing evidence, contradictions, unsupported certainty, or invalid outputs.
- Return a pass, qualification, failure, or request for additional analysis.

**Inputs:** Analytical results, source data or evidence references, interpreted request, and proposed interpretation.

**Outputs:** Verification result, findings, qualified result, or recovery/replanning recommendation.

**Should not be responsible for:** Replacing the analysis layer entirely, inventing a corrected result without evidence, or producing a final response independently of the response-generation responsibility.

**Dependencies:** Analysis Capabilities, Data Access, Agent / Decision Layer, and Response Generation.

## 6.9 Response Generation

**Purpose:** Transform verified analytical results into an understandable response.

**Responsibilities:**

- Answer the user's request using verified results and evidence.
- Include relevant numerical evidence and analysis scope.
- Distinguish observed facts from interpretation and uncertainty.
- State material assumptions, exclusions, limitations, or verification issues.
- Produce clarification, unsupported-request, partial-result, and failure responses where appropriate.

**Inputs:** Verified results, verification findings, interpreted request, relevant context, and response constraints.

**Outputs:** A grounded user-facing response or a clear limitation/clarification message.

**Should not be responsible for:** Performing hidden calculations, inventing missing data, overriding safety boundaries, or presenting an unverified result as established fact.

**Dependencies:** Verification, Agent / Decision Layer, Request Boundary, and Observability.

## 6.10 Observability

**Purpose:** Capture enough information to understand system and agent behavior during an execution.

**Responsibilities:**

- Record material execution stages and status transitions.
- Record decisions, selected analyses, action outcomes, verification status, and errors.
- Associate events with an execution or session identifier where applicable.
- Support debugging, testing, evaluation, and later improvement.
- Avoid unnecessary sensitive transaction details in observable records.

**Inputs:** Events and metadata emitted by the logical components.

**Outputs:** Execution history or diagnostic information according to a later observability design.

**Should not be responsible for:** Changing analytical results, deciding user-facing responses, or retaining sensitive data without a justified requirement.

**Dependencies:** All components that emit material events, plus future security and privacy decisions.

# 7. Logical Data Flow

The normal high-level flow is:

```text
User
  -> Request Boundary
  -> Input Validation
  -> Request Understanding
  -> Agent Decision
  -> Analysis Selection
  -> Data Access
  -> Deterministic Analysis
  -> Observation
  -> Verification
  -> Response Generation
  -> User
```

The flow represents responsibilities rather than a fixed one-pass implementation. The conceptual runtime established by the requirements is:

```text
Understand -> Plan -> Act -> Observe -> Validate -> Update -> Replan -> Verify -> Respond
```

The system may revisit earlier stages when:

- The request is ambiguous and clarification is needed.
- Required data is missing or invalid.
- An analysis action fails.
- An analysis result is empty or insufficient.
- Verification finds an inconsistency or unsupported conclusion.
- Additional analysis is needed to answer a multi-step request.
- The original plan is no longer appropriate after observing an intermediate result.

The system should preserve enough state to distinguish completed, failed, pending, and verified work during the execution. Detailed runtime transitions belong to Agent Design.

# 8. Agent vs. Non-Agent Responsibilities

The following classification is conceptual. Some responsibilities may be hybrid, and the exact division will be refined during Agent Design.

| Responsibility | Agent/Reasoning | Deterministic System Logic | Why |
|---|---|---|---|
| Natural-language request interpretation | Primary | Supporting validation | Language and context must be interpreted, while required fields and supported scope can be checked deterministically. |
| Determining analytical intent | Primary | Supporting constraints | The agent can identify intent; system rules constrain it to supported analyses. |
| Deciding which analysis is needed | Primary | Supporting capability registry/boundary | Selecting and sequencing capabilities is an agent responsibility, while available operations remain explicit. |
| Arithmetic | Not primary | Primary | Numerical calculations should be repeatable and checked against transaction data. |
| Filtering | Not primary | Primary | Filter behavior should follow explicit scope and inclusion rules. |
| Aggregation | Not primary | Primary | Totals and grouped values should not depend on free-form generation. |
| Period comparison | Supporting interpretation | Primary calculation | Period definitions may require interpretation, but comparison values should be computed deterministically. |
| Pattern detection where deterministic rules are sufficient | Not primary | Primary | Repeatable rules should be used where they adequately define recurrence, change, or unusualness. |
| Pattern interpretation | Primary | Supporting evidence | The agent may explain a detected pattern, but the explanation must remain tied to evidence. |
| Result validation | Hybrid | Primary checks | Deterministic consistency checks should be used where possible; reasoning may assess whether the result addresses the request. |
| Explanation generation | Primary | Supporting result structure | Language generation can make results understandable, but it must consume verified evidence and scope. |
| Handling ambiguity | Primary | Supporting validation and boundaries | The agent can ask focused clarification questions while deterministic rules identify missing or invalid fields. |
| State management | Hybrid | Primary state representation | The agent uses state to decide what to do; the surrounding system must preserve enough state to make execution inspectable. |
| Safety and scope boundaries | Hybrid | Primary enforcement where possible | Reasoning may recognize prohibited requests, but explicit system boundaries should prevent unsupported actions from being executed. |

The guiding principle is: **the agent should decide and interpret; deterministic capabilities should calculate and verify wherever possible.** This is a design principle, not an absolute requirement that excludes hybrid behavior.

# 9. Agent Runtime Boundary

The agent begins after a request and relevant input have passed through the applicable validation boundary, or after validation has produced findings that the agent must address. It receives:

- The interpreted or partially interpreted user request.
- Relevant conversation context when available.
- A description of the available transaction-data scope.
- Available analytical capabilities and their conceptual limits.
- Current execution state, observations, errors, and verification findings.

The agent can reason over the user request, authorized transaction-data context, available analytical results, and state associated with the current task. It can request actions through analysis and data-access boundaries, ask for clarification, choose to stop safely, or request response generation.

The agent receives action results, intermediate observations, status, limitations, and verification outcomes. It maintains enough short-lived execution state to know what has been understood, planned, attempted, observed, verified, and completed. Requirements for long-lived memory are not assumed.

Control returns to the surrounding system when:

- The agent requests validation or clarification.
- An analytical capability is requested.
- Verification is requested or completed.
- A response or safe failure should be returned.
- An unrecoverable system failure occurs.

The agent should not directly control payments, money movement, banking operations, external financial actions, storage infrastructure, deployment infrastructure, or unbounded access to sensitive data. Detailed state representation, planning, action schemas, execution loops, prompts, recovery behavior, and agent evaluation belong in `docs/04_agent_design.md`.

# 10. Interfaces Between Components

These are conceptual contracts, not APIs, classes, function signatures, or protocols.

## 10.1 User <-> Request Boundary

- **Caller:** User.
- **Receiver:** Request Boundary.
- **Information exchanged:** User request, transaction-data input, follow-up context, and user-facing response.
- **Expected behavior:** Receive input and return an understandable response, clarification, limitation, or safe failure.
- **Failure possibilities:** Unreadable input, unsupported interaction, incomplete request, or unexpected boundary failure.

## 10.2 Request Boundary <-> Validation

- **Caller:** Request Boundary.
- **Receiver:** Input Validation.
- **Information exchanged:** Raw or normalized request and transaction-data input within the supported scope.
- **Expected behavior:** Validation reports whether inputs are usable, incomplete, malformed, ambiguous, or limited.
- **Failure possibilities:** Unsupported format, malformed data, missing required information, or validation failure.

## 10.3 Validation <-> Agent

- **Caller:** Input Validation.
- **Receiver:** Agent / Decision Layer.
- **Information exchanged:** Validated inputs, data-quality findings, request constraints, and clarification needs.
- **Expected behavior:** The agent uses findings to continue, clarify, narrow, or stop.
- **Failure possibilities:** Validation output is incomplete, contradictory, or insufficient to determine a safe next action.

## 10.4 Agent <-> Analysis Capabilities

- **Caller:** Agent / Analysis Orchestration.
- **Receiver:** Selected analytical capability.
- **Information exchanged:** Analysis intent, scope, operation parameters, data requirements, and execution context.
- **Expected behavior:** The capability performs only the requested supported operation and returns results with scope, evidence references, status, and limitations.
- **Failure possibilities:** Unsupported operation, invalid parameters, missing data, empty result, execution error, or inconsistent result.

## 10.5 Analysis <-> Data Access

- **Caller:** Analysis Capability.
- **Receiver:** Data Access / Transaction Data Layer.
- **Information exchanged:** Scoped request for transaction records and relevant data metadata.
- **Expected behavior:** Return only the relevant authorized records and identify missing or ambiguous data.
- **Failure possibilities:** Unavailable data, unsupported field, malformed record, access boundary, or data-source failure.

## 10.6 Analysis <-> Verification

- **Caller:** Analysis Capability or Analysis Orchestration.
- **Receiver:** Verification.
- **Information exchanged:** Analytical results, calculation context, inclusion rules, source references, and proposed observations.
- **Expected behavior:** Check calculation correctness, scope consistency, and evidence traceability.
- **Failure possibilities:** Result mismatch, missing evidence, invalid scope, unsupported interpretation, or verification failure.

## 10.7 Verification <-> Agent / Response Generation

- **Caller:** Verification.
- **Receiver:** Agent / Decision Layer and Response Generation.
- **Information exchanged:** Verification status, findings, qualified results, and recommended next action.
- **Expected behavior:** Passed results may proceed; qualified or failed results must be revised, limited, clarified, or withheld.
- **Failure possibilities:** Verification is inconclusive, required evidence is unavailable, or no safe response can be formed.

## 10.8 System <-> Observability

- **Caller:** All logical components.
- **Receiver:** Observability.
- **Information exchanged:** Execution identifier, timestamps, stage, action, status, errors, result metadata, verification state, and model or computational usage where applicable.
- **Expected behavior:** Capture enough information to reconstruct material execution behavior without unnecessary sensitive data exposure.
- **Failure possibilities:** Missing event, unavailable observability mechanism, sensitive-data leakage, or incomplete execution history.

# 11. State and Context at System Level

The system should distinguish the following conceptual objects:

- **Request:** The user's current question or instruction, including the intended scope as understood or still unresolved.
- **Conversation context:** Relevant prior user and system exchanges needed to interpret a follow-up question.
- **Agent execution state:** The current task status, plan, actions, observations, errors, and next decision.
- **Analytical results:** Outputs from one or more analysis capabilities, including scope, calculations, evidence references, and limitations.
- **Verified results:** Analytical results that have passed the applicable verification checks or have been explicitly qualified.
- **Final response:** The user-facing answer, clarification, limitation, or safe failure generated from the verified execution state.

During one task, the system should conceptually persist enough information to connect the request to the selected analysis, data scope, intermediate observations, verification outcome, and final response. This supports traceability and prevents response generation from becoming detached from the work that produced the result.

## 11.1 Short-lived execution state

Short-lived state is required during one agent run. It may include the interpreted request, selected scope, planned operations, completed actions, action results, intermediate observations, verification status, errors, and the next action. The exact representation is TBD and belongs to Agent Design.

## 11.2 Conversational context

Conversational context contains prior exchanges and relevant prior analytical results needed to resolve a follow-up request. It should be limited to context that remains valid and should not cause the system to infer unsupported personal circumstances. The required context length and retention behavior are TBD.

## 11.3 Persistent state

Persistent state would survive beyond a session and could support longer-term history, reusable data, or ongoing user tasks. Persistent storage and persistent memory are not required by this system design. Whether they are needed for a later version remains TBD and must be justified by requirements.

# 12. Error Handling Strategy

The high-level error strategy is to avoid silently continuing with a materially invalid, ambiguous, unsupported, or unverified result. The exact retry and recovery mechanisms belong to Agent Design and Implementation.

| Situation | Expected high-level behavior |
|---|---|
| Invalid transaction data | Reject, isolate, or qualify the invalid records; explain what prevents reliable analysis. |
| Missing required information | Request the missing information when the user can reasonably provide it, or report the limitation. |
| Ambiguous user request | Ask a focused clarification question when different interpretations would materially change the result. |
| Unsupported request | Explain the supported boundary and decline the unsupported part without fabricating an answer. |
| Analysis failure | Report the failure, retry or choose another supported analysis only when justified, or return a bounded inability to answer. |
| Tool or action failure | Treat the action as unsuccessful, record the failure, and allow the agent to recover, replan, or stop safely. |
| Empty result | Explain that no matching data was found or that the available data cannot support the requested conclusion. |
| Inconsistent result | Prevent the inconsistent result from being presented as reliable; investigate, reanalyze, qualify, or stop. |
| Verification failure | Do not present the result as verified; revise the analysis, present a qualified partial result, request clarification, or report inability to answer. |
| Model or reasoning failure | Fall back to a bounded clarification or failure response rather than inventing intent, calculations, or evidence. |
| Unexpected system failure | Stop safely, avoid exposing unnecessary sensitive information, and return a clear inability-to-complete response where possible. |

Partial results are acceptable only when their scope and limitations are explicit and the remaining failure does not make them misleading.

# 13. Verification Architecture

Verification is separate from response generation because a fluent response can be understandable while still containing an incorrect calculation or unsupported conclusion. Separating verification gives the system a deliberate opportunity to check the work before presenting it.

## 13.1 Outputs requiring verification

Verification is particularly important for:

- Spending totals and other numerical values.
- Period comparisons and reported changes.
- Category or contributor rankings.
- Recurring-pattern findings.
- Potentially unusual or noteworthy activity.
- Multi-step analyses where one intermediate result affects later conclusions.
- Claims that a pattern is supported by particular transactions.

## 13.2 Calculation correctness

Calculation correctness concerns whether the numerical result follows from the relevant records, filters, grouping, period boundaries, transaction directions, and inclusion rules. Deterministic checks should be used where possible, including recomputation or consistency checks against the source evidence.

## 13.3 Interpretation groundedness

Interpretation groundedness concerns whether the explanation follows from the verified analytical result and available evidence. A numerically correct increase in a category does not by itself prove why the increase occurred. A repeated charge does not by itself prove that it is a subscription, authorized, or still active. The system must keep those distinctions visible.

## 13.4 Verification failure

If verification finds a mismatch, missing evidence, unsupported certainty, or another material problem, the result must not be presented as established. The system may revise the analysis, request additional information, provide a clearly qualified partial result, or report that it cannot answer reliably.

# 14. Observability Architecture

Observability should eventually make material system and agent behavior inspectable for debugging, testing, evaluation, and iterative improvement. It should not require exposing all raw transaction data in logs.

Conceptual events include:

- Request received.
- Input validation completed and validation status.
- Request understanding completed.
- Agent decision or next-action selection.
- Analysis selected.
- Analysis execution started and completed.
- Analysis result or empty result produced.
- Observation recorded.
- Verification requested and completed.
- Replanning or recovery occurred.
- Error or unsupported request occurred.
- Clarification requested.
- Final response generated and returned.

Useful metadata may include:

- Execution or session identifier.
- Timestamps.
- Action sequence and stage.
- Status and outcome.
- Error category and relevant diagnostic detail.
- Analysis scope and capability name.
- Verification status.
- Model-related information where applicable.
- Computational or model usage where applicable.
- References to evidence without unnecessary sensitive transaction contents.

The event format, retention policy, privacy controls, and observability technology are TBD.

# 15. Security and Privacy Architecture

Transaction data is sensitive personal financial information. The system should therefore minimize exposure while preserving enough information for the requested analysis and verification.

At a high level:

- Components should receive only the transaction fields and context needed for their responsibilities where practical.
- User requests and analytical responses should avoid repeating sensitive details that are not necessary to answer the question.
- Observability should avoid placing raw transaction data or unnecessary identifying information into logs or execution records.
- Data should not be persisted beyond the required task or supported session without a justified requirement.
- Execution state and observability data should be protected according to the sensitivity of the information they contain.
- Data access should remain within the authorized project scope and should not imply access to external financial systems.
- If the system evolves beyond a local prototype or supports multiple users, authentication, authorization, access isolation, secure transport, storage protection, and retention policies will need explicit design.

The system design does not select authentication, encryption, hosting, storage, or compliance mechanisms. Detailed security and privacy implementation remains TBD.

# 16. Deployment Model - Initial vs Future

## 16.1 Initial prototype

The initial prototype should use the simplest deployment model sufficient to demonstrate the requirements and evaluate the core agentic analysis loop. Several logical components may run within one application or process. No distributed services, production infrastructure, persistent database, external financial integration, or hosted deployment is required by this design.

The exact interface and local execution arrangement are TBD and will be selected during implementation planning.

## 16.2 Future evolution

If later requirements justify it, the logical architecture should be able to evolve toward:

- Persistent databases or other durable storage.
- External APIs or additional data sources.
- Containerized or hosted deployment.
- Larger workloads and more users.
- More complex workflows.
- Additional specialized components or agents.
- Stronger operational controls.

These are future options, not initial architecture decisions. Deployment architecture will be refined after implementation and operational requirements are better understood.

# 17. Scalability and Extensibility

The system should evolve through stable logical boundaries rather than by expanding one opaque component. The following boundaries are especially important:

- **Input boundary:** Additional transaction formats should be introduced behind validation and data-normalization responsibilities.
- **Data boundary:** Additional storage or data sources should provide scoped transaction data without requiring analysis capabilities to understand their internals.
- **Analysis boundary:** New analytical capabilities should expose clear inputs, outputs, evidence references, limitations, and status.
- **Agent boundary:** More complex planning or workflows should remain separate from the deterministic calculations they coordinate.
- **Verification boundary:** New analyses should be able to define or reuse checks before their results become user-facing claims.
- **Response boundary:** Richer interfaces should consume the same grounded results and response constraints rather than reimplementing financial reasoning.
- **Observability boundary:** New actions and components should emit inspectable events without coupling their behavior to a particular logging technology.

Potential future changes include additional transaction formats, analytical capabilities, persistent storage, external data sources, richer interfaces, larger datasets, multiple users, more complex agent workflows, and additional specialized agents. None of these systems should be designed in detail or implemented in the MVP.

# 18. Architecture Alternatives Considered

## Alternative A - Traditional analytics system

A fixed analytics pipeline or dashboard could provide predefined totals, categories, comparisons, and visualizations. This approach may be straightforward and useful for repeatable reports, but it may be less flexible for context-dependent questions, conversational follow-ups, and multi-step requests whose analysis is not known in advance.

## Alternative B - LLM-only system

An LLM-only approach could accept transaction data and directly generate answers. It may handle natural-language interaction flexibly, but it would create unnecessary risk for arithmetic, filtering, aggregation, traceability, and verification if the reasoning system were also treated as the calculation source of truth.

## Alternative C - Agent plus deterministic analytical capabilities

In this approach, the agent interprets the request, determines the required work, and coordinates analytical capabilities. Deterministic capabilities calculate and organize transaction results, while verification checks important outputs and response generation explains the verified evidence.

Alternative C is the current preferred conceptual direction because it addresses both sides of the requirements: context-dependent interaction and grounded, verifiable financial analysis. This is not a claim that it is universally superior to the alternatives. Its usefulness, complexity, and quality remain subject to implementation and evaluation.

# 19. Initial Architecture Decision

The initial system should conceptually follow:

```text
User Request
  -> Validation
  -> Agent / Reasoning
  -> Analytical Capabilities
  -> Transaction Data
  -> Verification
  -> Grounded Response
```

The initial implementation should favor a simple, modular application with logical boundaries rather than distributed infrastructure. The first version should contain one initial agent and deterministic analytical capabilities required by the selected MVP use cases.

This decision does not select:

- A framework or orchestration library.
- A database or storage technology.
- A cloud or hosting provider.
- A language model or model provider.
- A frontend or interface framework.
- A multi-agent architecture.
- External financial APIs.
- Containerization or distributed deployment.

Those decisions belong to later design and implementation phases and should be introduced only when justified by requirements and evidence.

# 20. Design Decisions and Rationale

| Decision | Rationale | Status |
|---|---|---|
| Investigate agent-based interaction for context-dependent analysis | User questions may require different combinations of filtering, grouping, comparison, and interpretation than fixed reports can anticipate. | Decided |
| Use deterministic computation for appropriate numerical operations | Totals, filtering, aggregation, and comparisons require repeatable results and are easier to verify through conventional computation. | Decided |
| Treat verification as a first-class responsibility | Correct calculations and grounded interpretations should be checked before important outputs are presented. | Decided |
| Maintain logical component boundaries | Separation supports testing, traceability, maintainability, and future change even when components initially share one application. | Decided |
| Keep the initial architecture simple | The MVP should demonstrate the core loop without infrastructure that current requirements do not justify. | Decided |
| Preserve future extensibility without premature infrastructure | Clean interfaces can support later storage, data sources, workflows, or specialized components without implementing them now. | Decided |
| Use one initial agent for the MVP | The requirements establish an initial agent; additional agents are not needed to demonstrate the core loop. | Decided |
| Define detailed agent runtime and state separately | Planning, action selection, execution, observation, and recovery need deeper treatment than this system-level document provides. | Tentative boundary; detailed design TBD |
| Select exact analytical capability contracts | The requirements identify analytical responsibilities, but exact operations, inputs, outputs, and limits depend on data design. | TBD |
| Select data access and persistence approach | Input formats, schema, source strategy, and persistence need data and implementation design. | TBD |
| Select model or reasoning mechanism | The system may use intelligent reasoning, but no provider or model is established. | TBD |
| Select interface, deployment, security, and observability technologies | These depend on implementation and operational requirements that are not yet defined. | TBD |

# 21. Open Questions / TBD

The following system-design questions remain unresolved:

- What exact agent architecture will satisfy the initial runtime requirements?
- How will agent execution state be represented?
- What conceptual tool or analytical-capability interface is needed?
- Which exact analytical capabilities belong in the MVP?
- What is the supported transaction schema and data access mechanism?
- Which input formats will be accepted?
- How much conversation context must be retained and for how long?
- Is persistent storage required for any MVP behavior?
- Which model or reasoning mechanism, if any, should support request understanding and interpretation?
- How should model interaction be bounded and verified?
- What interface will be used for the initial prototype?
- What observability information and retention behavior are required?
- What security and privacy controls are required for the selected implementation?
- What deployment environment is appropriate after prototype requirements are clarified?
- Are external APIs needed for any approved future capability?
- Would multiple specialized agents ever be justified by later requirements and evaluation?
- What performance, workload, cost, and operational targets should be defined later?

These questions remain TBD. They must be resolved through the next design, data, implementation, and evaluation phases rather than by assuming a preferred technology or architecture.

# 22. Handoff to Next Design Phase

`docs/03_system_design.md` establishes the overall system boundaries, logical components, responsibilities, conceptual interfaces, data flow, verification approach, observability expectations, privacy boundaries, and architectural principles for the Personal Finance Agent.

The next document should be `docs/04_agent_design.md`. It should focus specifically on the internal design of the agent, including:

- Agent responsibilities.
- Runtime loop.
- State and context.
- Planning.
- Action and tool selection.
- Execution.
- Observation.
- Validation.
- Verification.
- Replanning.
- Failure recovery.
- Response generation.
- Agent boundaries.
- Tool contracts.
- Agent-specific evaluation considerations.

The agent design should be derived from this system design and the requirements rather than independently introducing a different architecture or technology choice.
