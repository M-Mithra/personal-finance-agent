# 1. LLM Integration Design Overview

This document defines the architectural boundary between the implemented deterministic agent runtime and a future LLM-based reasoning layer. It derives from the objectives in `docs/01_problem_and_objectives.md`, the requirements in `docs/02_requirements.md`, the system boundaries in `docs/03_system_design.md`, the agent design in `docs/04_agent_design.md`, the data design in `docs/05_data_design.md`, the implementation in `docs/06_implementation.md`, the testing and evaluation approach in `docs/07_testing_and_evaluation.md`, the deployment and operations approach in `docs/08_deployment_and_operations.md`, and the decision log in `docs/09_decisions_and_changes.md`.

The purpose of this document is not to redesign the system. The deterministic foundation (canonical transactions, validation, analytics, verification) and the deterministic agent runtime (state, understanding, planning, tools, replanning, response generation) are the working system and remain authoritative. This document defines where and how an LLM may participate inside that existing runtime.

## 1.1 Why an LLM is being introduced

The deterministic runtime handles a narrow set of supported intents through explicit keyword matching, structured planning, bounded replanning, and template response generation. It is reliable, reproducible, and testable, but it generalizes poorly across varied natural-language phrasing, contextual references, conversational follow-ups, and novel combinations of supported tools. An LLM is introduced to provide flexible interpretation and reasoning where deterministic rules are brittle.

This is not a substitution of reasoning for computation. The project philosophy in `docs/01_problem_and_objectives.md` is to use deterministic computation wherever conventional software provides stronger correctness guarantees, and to use intelligent reasoning only where contextual interpretation, flexible interaction, or decision-making genuinely benefit from it.

This project is intended to learn agent engineering, not merely to demonstrate an LLM call. The value of this phase is establishing the lifecycle, tool contracts, verification wiring, state representation, and evaluation harness that a future model will use. Designing the boundary before implementation ensures those interfaces are stable before a provider is chosen.

## 1.2 What problem the LLM solves that deterministic logic solves poorly

- **Varied natural-language phrasing:** Users can ask the same analytical question in many ways; a fixed keyword strategy matches only a narrow subset.
- **Contextual interpretation:** Expressions such as "last month", "that category", or "about the same time" require resolving references against conversation context and prior results.
- **Planning flexibility:** Multi-step investigations such as explaining a spending increase require deciding which sequence of supported tools answers the question, based on intermediate results.
- **Interpretation of structured evidence:** Translating verified category and merchant totals into an understandable, evidence-supported explanation.
- **Conversational follow-up:** Resolving short follow-up questions against the immediately preceding exchange.

## 1.3 How the LLM fits into the existing architecture

The LLM participates inside the existing runtime at discrete, replaceable boundaries rather than replacing the runtime. The runtime remains the control boundary that owns execution, state, validation, verification, and termination. The LLM is a decision and interpretation component that:

- receives constructed context (request, intent, tool definitions, observations, verification results);
- returns structured decisions such as an interpreted intent, a selected next action, or a response proposal;
- never executes tools directly and never accesses the transaction dataset directly.

This matches the provider-neutral boundary philosophy already implemented: `runtime/understanding.py` was built to be replaceable by an LLM-based understanding module without redesigning the runtime.

## 1.4 Why the integration is designed before implementation

- The deterministic runtime and its boundaries must remain stable so the LLM slice does not require a redesign of the working system.
- Tool contracts, verification wiring, and state/trajectory representations must be defined before a model is asked to produce tool calls.
- Evaluation harnesses for both final responses and trajectories should exist before model output introduces nondeterminism.
- Provider and SDK choice should not drive architecture. A provider-neutral interface makes different models comparable without code changes.

The goal is to preserve everything that makes the deterministic system trustworthy and to add LLM reasoning only where it adds genuine value.
# 2. LLM Responsibilities

## 2.1 Architectural responsibilities

The LLM may eventually handle the following responsibilities. These are architectural responsibilities: they define where model reasoning can be used, not a commitment that all are implemented immediately.

- **Natural-language request understanding:** Recognizing what the user is asking from free-form text.
- **Intent interpretation:** Mapping the request to a supported intent, periods, dimensions, and constraints.
- **Contextual interpretation:** Resolving references in follow-up questions using conversation and execution context.
- **Planning:** Proposing an ordered sequence of analytical steps for the interpreted request.
- **Deciding which available analytical tools are needed:** Selecting among the registered tools on the basis of the plan and observed evidence.
- **Interpreting structured analytical results:** Reading structured totals, category and merchant contributions, and evidence references.
- **Deciding whether additional evidence is needed:** Determining whether the current observations answer the request or whether follow-up tools are warranted.
- **Generating grounded natural-language responses:** Producing user-facing text that reflects the verified evidence.
- **Handling conversational follow-up questions:** Maintaining continuity across turns.

Each responsibility maps to an existing runtime boundary (`runtime/understanding.py`, `runtime/planning.py`, `runtime/replanning.py`, `runtime/response.py`). The deterministic implementations remain the fallback baseline and the subject of incremental replacement per supported intent.

## 2.2 Distinction from the first implementation scope

Not all responsibilities must be implemented in the first model-powered slice. Section 22 defines the first scope: the spending-change explanation scenario ("Why did my September spending increase?"), which exercises understanding, planning/tool selection, deterministic analysis, verification, observation feedback, additional tool selection, and grounded response generation in a single trajectory. Other intents remain on the deterministic path until that first slice is validated by evaluation.
# 3. LLM Non-Responsibilities

The LLM must not be treated as the source of truth for the following operations. For each, a deterministic system responsibility exists and remains authoritative:

| Operation | Why deterministic logic is authoritative |
|---|---|
| Arithmetic | `Decimal` arithmetic is exact and testable; model arithmetic is probabilistic and cannot be trusted without independent verification. |
| Financial aggregation | Sums and totals must be reproducible from the underlying transactions. |
| Transaction filtering | Inclusion/exclusion rules (direction, currency, period) must be deterministic and traceable. |
| Date/period calculations | Calendar boundaries are exact (`datetime.date`, `Period`); interpreting them statistically is error-prone. |
| Category totals | Grouping and totals must reconcile with the transaction set. |
| Merchant totals | Contributor rankings must be deterministic and evidence-backed. |
| Percentage calculations | Differences and percentages must be exact decimal computations. |
| Numerical comparisons | Comparisons such as "largest expense" must follow a defined deterministic rule. |
| Numerical verification | Verification is an independent recomputation performed by `verification.py`. |
| Evidence reconciliation | Checking that totals match their referenced transactions is a deterministic invariant. |
| Direct access to raw financial storage | Access goes through the data boundary (`data.py`); the model never receives or edits raw storage. |
| Direct execution of arbitrary code | Tool calls are the only execution path and are validated by the runtime. |
| Financial transactions, banking operations | Out of scope by design (DEC-001); no money movement by any component. |
| Tax decisions, investment decisions | Out of the spending-analysis scope of the system. |

The general principle: the LLM may request, interpret, and explain, but it does not compute financial facts and it does not mutate or directly access financial records. All numerical facts presented in a response must originate from verified deterministic tool results. This reflects DEC-003 (Deterministic Computation vs. LLM Reasoning) in `docs/09_decisions_and_changes.md`.

# 4. LLM Boundary

The recommended architecture is:

```text
User
  -> Agent Runtime
  -> LLM
  -> structured tool/action request
  -> deterministic analytical tool
  -> structured result
  -> verification
  -> AgentState
  -> LLM
  -> grounded response
```

## 4.1 Information flow directions

- **User -> Agent Runtime:** The request enters through the runtime entry boundary (`run(request, transactions)` / `Agent.execute`).
- **Runtime -> LLM:** The runtime constructs context (request, intent, tool definitions, relevant state, observations, verification results) and sends it to the LLM through the provider-neutral interface (Section 16).
- **LLM -> Runtime:** The LLM returns a structured decision. When the decision is a tool call, it is a structured action request containing a tool name, arguments, and optionally a rationale (Section 7).
- **Runtime -> LLM (results):** The runtime validates, executes, observes, and verifies the action, then returns the structured result and its verification status to the LLM as updated context.

## 4.2 What the LLM cannot do

- The LLM must not directly call Python functions or methods of the analytical layer.
- The LLM must not manipulate or read the transaction dataset directly; it only receives structured results and scoped context constructed by the runtime.
- The LLM must not bypass validation, verification, or the tool registry.
- The LLM must not initiate financial or banking operations.

The runtime is the single control boundary through which all information flows in either direction. The LLM is a component inside the boundary, not a peer that can reach around it.
# 5. LLM Interaction Model

The conceptual interaction lifecycle is:

```text
Request
  -> construct context
  -> LLM reasoning
  -> structured decision/tool call
  -> validate tool call
  -> execute deterministic tool
  -> observe result
  -> verify result
  -> update state
  -> provide relevant result back to LLM
  -> LLM decides whether more evidence is required
  -> repeat if necessary
  -> final verification
  -> response generation
```

Key properties:

- **The LLM participates inside the existing runtime rather than replacing it.** The runtime loop (`runtime/agent.py`) remains the owner of iteration, state mutation, verification triggering, and termination. The LLM supplies decisions at defined points: understanding, planning/tool selection, evidence sufficiency, and response generation.
- **Every iteration is observable.** Each model decision, validated tool call, observation, and verification record is appended to the `AgentState` trajectory, exactly as the deterministic runtime records them today.
- **The loop is bounded.** The runtime enforces maximum steps and maximum tool calls (Section 14). Repeated or looping model behavior terminates with an explicit status rather than continuing indefinitely.
- **The deterministic path remains the fallback.** For intents not yet covered by the LLM slice, and whenever model output is invalid or unsafe, the runtime either falls back to the deterministic implementation or responds with a clear limitation.

This model produces the same lifecycle as the implemented deterministic runtime, so evaluation of trajectories (Section 21) applies unchanged to model-powered executions.

# 6. Context Construction

## 6.1 What should be provided to the LLM

Context for a reasoning step should include only what is relevant to that step:

- **Current user request:** The original request text, preserved verbatim.
- **Interpreted/current intent:** The current understanding of what is being asked, including identified periods and constraints when available.
- **Relevant AgentState:** The portion of state relevant to the current step: current plan, pending/completed actions, errors, and response objective.
- **Available tool descriptions:** The names, purposes, input contracts, and output structures of the registered tools.
- **Previous actions:** Completed actions and their summaries, so the model can avoid redundant work and follow up consistently.
- **Analytical observations:** Structured results of executed tools.
- **Verification results:** The trust classification of each result (verified, failed, inconclusive, unverified).
- **Relevant conversation history:** Earlier exchanges needed to resolve references in a follow-up question.
- **Assumptions and ambiguity information:** Material interpretations (for example, which prior month was selected) and unresolved ambiguities.

## 6.2 What must not be included by default

The entire raw transaction dataset must **not** be automatically included in every LLM prompt. Transactions enter model context only as structured analytical results produced by the deterministic tools, and only to the extent required for the current reasoning step. This protects privacy (Section 19), bounds context size and cost (Section 18), and keeps the model reasoning over verified evidence rather than raw records it might mis-transcribe or mis-summarize.

## 6.3 Context layers

Distinguish conceptually distinct layers. This is a taxonomy, not a prescribed prompt format:

- **System instructions:** Stable policy governing scope, safety, tool usage, grounding, and verification rules (Section 17).
- **Task/request context:** The current question, periods, dimensions, and constraints.
- **Tool definitions:** Names, input contracts, output structures, and status semantics for the registered tools.
- **State/evidence context:** Completed actions, observations, verification records, and assumptions relevant to the current step.
- **Conversation context:** Prior exchanges needed for follow-up resolution.

The exact selection, ordering, size limits, and serialization of these layers are TBD (Section 26). The mechanism should be measured and tuned after the first slice rather than optimized speculatively.
# 7. Tool-Calling Contract

## 7.1 The structured action request from the LLM

The LLM must express any need for analytical work as a structured tool/action request that contains at least:

- **Tool/action name:** One of the names registered in the tool registry (`TOOLS` in `runtime/tools.py`).
- **Arguments:** Concrete argument values matching the selected tool's input contract (for example, a period and an optional limit).
- **Structured rationale/purpose (optional but recommended):** A short structured reason for the call that supports observability and trajectory evaluation without becoming prose.

This mirrors the existing `Action` dataclass (`name`, `params`, `purpose`). The LLM's structured decision is mapped to an `Action` only after validation succeeds.

## 7.2 Runtime validation (mandatory)

The runtime must validate every proposed tool call before execution:

- **Tool existence:** The requested name must exist in the registered tool set.
- **Argument contract:** Arguments must match the tool's expected parameters (type and required/optional status).
- **Required parameters present:** Every required parameter must be supplied (for example, `period` for single-period tools; `period_a`/`period_b` for period comparison).
- **Value validity:** Values must be valid instances (a `Period`, a sequence of `Transaction`s, a valid currency when restricted), not empty placeholders or malformed structures.
- **Permission in current state:** The action must be permitted at the current point of the execution (for example, no tool calls after termination, no calls that violate scope constraints).

Invalid tool calls **must not execute**. A rejected call is recorded as an error/rejection in state and may be returned to the model as a structured correction signal, subject to the bounded retry policy (Sections 13 and 14). A tool call can be rejected for any individual validation failure; the runtime does not attempt to "repair" invalid arguments itself.

## 7.3 No arbitrary code execution

The LLM cannot request execution of arbitrary code. Tool calls are the only execution path available to it, and each tool maps to a specific deterministic analytical capability. Nothing claimed to be "just a function call" is ever executed outside `execute_tool` inside the runtime.
# 8. Tool Result Contract

After a tool executes, the LLM receives a structured result that exposes:

- **Tool/action identity:** Which tool was executed (name and the action identifier when available).
- **Analytical result:** The typed structured result produced by the analytical capability (for example, `SpendingSummary`, `CategoryAnalysis`, `PeriodComparison`, `MerchantAnalysis`, `NoteworthyAnalysis`), carrying the numeric values, period, currency, status, warnings, and evidence references.
- **Status:** Whether the action succeeded, returned an empty result, or failed, with the structured distinction the tool layer already provides.
- **Relevant evidence:** References to the transactions or computed evidence that support the result (the IDs embedded in the result dataclasses).
- **Verification status:** The independent trust classification (verified, failed, inconclusive, unverified) produced by `runtime/checks.py`.
- **Errors when applicable:** Structured error information for failed actions.

Tool results remain structured values. The tool layer does not produce natural-language prose for the LLM to reason over; the LLM reads the structured fields directly. This mirrors the existing `Observation` and `VerificationRecord` dataclasses in `runtime/state.py`.

Because numeric values are carried in structured form (exact `Decimal` amounts with their currency), the model is never asked to re-derive or re-format financial numbers. It interprets structure; it does not recompute.

# 9. Verification Interaction

The verification interaction follows this fixed data flow:

```text
Tool
  -> Result
  -> Independent Verification
  -> Trust Classification
  -> AgentState
  -> LLM
```

The LLM receives results only after verification has produced a trust classification and recorded it in state. The following behavior is defined for each trust level (matching `runtime/checks.py`):

| Trust classification | Meaning | LLM behavior |
|---|---|---|
| `verified` | All deterministic checks passed against the canonical transactions. | May be presented as an established financial fact. |
| `failed` | At least one check disagreed with the referenced transactions. | Must **not** be presented as an established financial fact. The response must acknowledge the failure or reason about its cause in qualified terms. |
| `inconclusive` | Verification could not establish trust (for example, an error or empty result with no numeric content). | May be discussed only with explicit qualification about its uncertainty. |
| `unverified` | No verifier is registered for the tool. | Treated as not established unless the runtime policy explicitly qualifies it otherwise. |

Two invariants are enforced regardless of model output:

1. **The LLM must not override a failed verification result.** The runtime guarantees that a failed result cannot be passed to the response generator as a trusted fact, whatever the model claims.
2. **A result failing verification must not be presented as an established financial fact.** If the model proposes a response that asserts an unverified or failed number as fact, the runtime rejects or qualifies that assertion before delivery.

Verification remains deterministic and independent of the LLM. The model's job is to reason correctly about the trust classification it is given, not to change it.
# 10. Planning and Replanning

## 10.1 Division of responsibility

The LLM may propose a plan or a next action, informed by the same structured inputs the deterministic planner uses (`runtime/planning.py`, `runtime/replanning.py`). The runtime remains responsible for:

- **Validating the proposed action:** Checking the tool name and arguments against the registered contract (Section 7.2).
- **Enforcing tool boundaries:** Executing only through `execute_tool`; never allowing arbitrary execution.
- **Executing the action:** Running the deterministic analytical capability and recording the observation.
- **Checking results:** Confirming status and recording what the result establishes and fails to establish.
- **Maintaining state:** Applying accepted model contributions to `AgentState` through validated, recorded updates.
- **Enforcing termination limits:** Maximum execution steps and maximum tool calls per request.
- **Triggering verification:** Running independent checks after important actions.
- **Preventing invalid or unsafe actions:** Rejecting calls that violate scope, tool, or safety rules.

The model decides; the runtime governs. A proposed plan is only materialized as executed state step by step, and every step is validated before it runs.

## 10.2 Example: "Why did my September spending increase?"

A possible LLM-guided trajectory is:

```text
1. period comparison        (September versus the comparison period)
2. observe increase
3. category analysis        (contributors to the change)
4. merchant analysis        (contributors to the change)
5. verify evidence
6. synthesize explanation
```

This is the same shape as the deterministic spending-change trajectory and demonstrates LLM-guided iterative investigation: the model chooses follow-up tools based on what the comparison revealed. The runtime validates each call, executes it deterministically, verifies the result, and records everything in state.

**This is not a hard-coded final architecture.** It is an initial example. The model may skip steps where evidence is sufficient, add other supported tools when warranted, or stop when the question is answered. The only fixed properties are the tool set, validation, verification, and termination boundaries.

# 11. Agent State Interaction

## 11.1 What the LLM reads

The LLM is given a constructed view of `AgentState` relevant to the current reasoning step, including the original request, current intent, plan, pending/completed actions, observations, verification records, errors, and assumptions. It never needs (and does not receive by default) the raw transaction dataset or unrelated state.

## 11.2 What the LLM may contribute

The LLM may propose:

- an **interpreted intent** (a structured intent that the runtime maps onto `Intent`);
- a **proposed plan** (an ordered set of structured actions);
- a **selected next action** (one structured tool/action request);
- an **interpretation of observations** (a structured reading of what the evidence establishes);
- a **proposed response** (natural language plus, where required, references to the evidence it rests on).

## 11.3 What the runtime remains authoritative for

- **Actual tool execution:** Only the runtime invokes analytical capabilities.
- **Actual analytical results:** Only deterministic tools produce numeric results.
- **Verification results:** Only `verification.py`/`runtime/checks.py` classify trust.
- **Execution history:** Only the runtime appends to the trajectory.
- **Errors:** Only the runtime records errors and statuses.
- **State transitions:** Only the runtime mutates `AgentState`.
- **Termination:** Only the runtime decides when execution stops.

## 11.4 Direct mutation is not permitted

The model must not be allowed to directly mutate arbitrary state fields. Its contributions are exposed as structured proposals that the runtime validates and applies through its own state-update path, each application recorded in the trajectory. This keeps the execution history trustworthy: it reflects what the runtime actually did, regardless of what the model output suggested.
# 12. Response Generation

## 12.1 Requirements for final responses

A final response must be:

- **Grounded in verified evidence:** Every financial claim is supported by a verified analytical observation in state.
- **Traceable to analytical observations:** Claims can be followed back to the specific tool results and evidence references that produced them.
- **Explicit about uncertainty:** Limitations, empty results, inconclusive verification, and missing data are stated rather than hidden.
- **Clear about the difference between computed facts and interpretations:** Computed facts (totals, differences, rankings) are distinguished from the model's interpretation of those facts.
- **Free of unsupported financial claims:** No invented numbers, invented contributors, or causal claims without evidence. Causal claims about the user's behavior remain outside scope (consistent with `docs/04_agent_design.md`, section 23).

## 12.2 Division of work

The LLM may turn structured, verified evidence into understandable natural language. It must not independently invent financial numbers or explanations unsupported by evidence. Two mitigations support this:

- The runtime supplies all numeric values as structured exact values (Section 8), so the model formats and interprets rather than recalculates.
- The runtime performs a final grounding check where practical: proposed response assertions are checked against observed evidence and verification records before delivery, mirroring Milestone 5's "final-response claim checks" in `docs/06_implementation.md`.

## 12.3 Partially deterministic output remains an option

Whether response generation remains partially deterministic (for example, numbers and scope constraints formatted by the runtime, with the model supplying only interpretation) is an open design question (Section 26). The deterministic `runtime/response.py` remains the baseline until the decision is made.

# 13. Error and Failure Handling

## 13.1 Expected LLM-related failures

- **Malformed model output:** Output that cannot be parsed into the expected structured decision.
- **Invalid tool call:** A structured tool request that fails validation.
- **Nonexistent tool:** A tool name outside the registered set.
- **Invalid tool arguments:** Present but incorrect arguments (wrong type, missing required values, invalid periods or currencies).
- **Model timeout:** The model did not respond within the timeout budget.
- **Model unavailable:** The provider or model could not be reached or returned a service error.
- **Context overflow:** The constructed context exceeds the model's context window.
- **Repeated tool calls:** The same call repeated without new information.
- **Planning loop:** The model keeps requesting work without converging.
- **Unsupported request:** A request outside the supported scope.
- **Insufficient evidence:** The data cannot answer the question even after analysis.
- **Verification failure:** Results fail independent verification or are inconclusive.

## 13.2 Fail-safe principle

Model failure must fail safely rather than silently producing a confident answer. Concretely:

- Invalid, malformed, or rejected model output is recorded as an error/rejection, not converted into a plausible-looking answer.
- Failures are classified as retryable (for example, a transient timeout or a repairable tool-call format) or terminal (for example, context overflow, unsupported request, repeated failures), and the runtime acts accordingly with bounded retry counts.
- Terminal failures produce an explicit response status and a clear limitation message (or a clarification request), never speculation.
- Verification failures cannot be converted into established facts (Section 9).

This mirrors the existing error handling in `runtime/agent.py`, extended with model-specific failure categories. The exact retry policy, timeout values, and fallback strategy are TBD (Section 26).
# 14. Guardrails

The following guardrails are architectural invariants enforced by the runtime loop, not prompt-only restrictions that the model can ignore. No external guardrail framework is introduced.

- **Allowed tools only:** The model can only request tools present in the registered tool set.
- **Structured tool calls:** Every tool request is a structured action with a name and arguments, never free-form instruction to "run code".
- **Argument validation:** Every tool call is validated before execution (Section 7.2).
- **Bounded execution steps:** A maximum number of reasoning/execution steps per request.
- **Bounded tool calls:** A maximum number of tool calls per request.
- **Verification requirements:** Important analytical results are verified before their numbers can be treated as established facts.
- **No arbitrary code execution:** No execution path other than validated tool calls.
- **No direct financial actions:** No money movement, banking, or payment operations.
- **No unsupported claims:** Responses cannot assert facts not supported by verified evidence.
- **No bypassing verification:** The model cannot waive, override, or redact verification (Section 9).
- **Explicit uncertainty:** Limitations and empty/inconclusive results are stated in responses.
- **Privacy-aware context construction:** Context sent to the model is minimized and contains no unnecessary raw transaction data (Sections 6 and 19).

These guardrails extend the safety boundaries already defined in `docs/04_agent_design.md` (section 23) and `docs/02_requirements.md`. They are described here at the architecture level; concrete limits (step counts, tool-call counts, timeout budgets) are TBD (Section 26).

# 15. Conversation and Follow-Up Context

## 15.1 Example interaction

```text
User:      "How much did I spend in September?"
Follow-up: "What about August?"
Follow-up: "Why was September higher?"
```

For such exchanges, the agent must preserve enough context to resolve references:

- "What about August?" refers to the same analysis (spending total) applied to a new period.
- "Why was September higher?" refers to the two periods already discussed and requires comparison plus contributor analysis.

The runtime keeps the relevant prior request, interpreted intent, prior results, and verification records available for follow-up resolution.

## 15.2 What is preserved and what is not

The agent should preserve relevant conversational context without automatically including unnecessary historical context in every interaction. Context selection should be relevance-based and bounded.

Distinguish two kinds of state:

- **Short-term execution state:** The current run's plan, actions, observations, and verification records (already modeled by `AgentState`). This is retained for the duration of the active interaction and is the primary substrate for follow-ups.
- **Longer-term conversational memory:** Prior turns and their interpretations, retained across turns but selected by relevance for each follow-up. This is not a general long-term memory system.

## 15.3 No persistent memory in this phase

Persistent memory (database, vector store, or durable conversation history) is not part of this phase and is explicitly excluded (Section 25). Follow-up context is held in memory for the active interaction. Whether durable conversation memory is ever needed remains an open question (Section 26), consistent with the deferred-memory decisions in `docs/04_agent_design.md` and `docs/06_implementation.md`.
# 16. Provider-Neutral LLM Interface

## 16.1 Conceptual abstraction: `LLMClient`

A single conceptual interface, `LLMClient` (the name is illustrative and not final), isolates the runtime from any specific model provider. Its responsibilities are:

- **Send structured context/instructions to a model:** The runtime passes the constructed context (Section 6) plus the relevant instruction layer (Section 17) in a provider-neutral structure.
- **Receive a structured model response:** The client parses and validates the model output into the runtime's structured decision types (intent, plan, tool call, response proposal). Model output whose structure cannot be validated is surfaced as a malformed-output error.
- **Expose model metadata where useful:** Model identity and version become part of observability (Section 20).
- **Surface errors/timeouts:** Provider errors, timeouts, service unavailability, and context-overflow conditions are surfaced to the runtime as typed statuses/errors, so the runtime can apply its fail-safe policy (Section 13).

## 16.2 What the rest of the runtime must not depend on

The runtime must not import or depend on any specific provider SDK. All provider-specific behavior lives behind the `LLMClient` interface, and the interface supports:

- a real provider-backed client, whose selection is deferred (Section 26);
- deterministic test doubles that return scripted structured responses, used for unit/integration tests and evaluation without a provider.

This continues the provider-neutral boundary philosophy already established for `runtime/understanding.py` in `docs/06_implementation.md` (section 3.2 and the module mapping table).

## 16.3 Non-goals for this phase

No provider is chosen, no SDK is installed, and no API credentials or provider environment variables are introduced in this phase. The provider, the exact interface signature and serialization, structured-output mechanism, timeouts, and retry policy are all TBD (Section 26). This document defines the boundary, not the binding.

# 17. Prompt and Instruction Architecture

## 17.1 Conceptual instruction layers

Prompts and instructions are organized in layers that map to stable responsibilities. Actual production prompts are not written in this design phase; this defines the structure they will follow:

- **System-level agent policy:** The constant framing of the agent's role, scope, and behavior across all interactions.
- **Scope and safety rules:** The financial-domain boundaries (no advice, no actions, no causal claims) and the guardrail rules (Section 14).
- **Tool usage rules:** How tools are named, what their contracts are, and the requirement to express work only as structured tool calls.
- **Grounding/verification rules:** The requirement to reason only from verified evidence and to respect trust classifications.
- **Task context:** The current request, interpreted intent, periods, and constraints (Section 6.3).
- **State/evidence context:** Completed actions, observations, verification records, and assumptions relevant to the current step.
- **Response-generation instructions:** How to format a grounded response, distinguish facts from interpretation, and state uncertainty.

## 17.2 Versioning and identification

Instructions/prompts should eventually be version controlled and identifiable so that behavior can be compared across versions and regressions can be attributed to a change. This aligns with the observability (Section 20) and evaluation (Section 21) requirements. The versioning mechanism (files, tags, identifiers) is TBD (Section 26).

No production prompts are written as part of this document, consistent with the design-before-implementation objective.
# 18. Context, Token, and Cost Considerations

## 18.1 Architectural considerations

The following factors shape how context is constructed and bounded:

- **Context size:** Number of tokens per interaction and its effect on reasoning quality, latency, cost, and error rates.
- **Unnecessary transaction data:** The largest avoidable cost driver. Raw transactions are excluded from context by default (Section 6.2); structured analytical results are compact by comparison.
- **Tool result size:** Tool results should remain a bounded summary of the analytical result (top contributors, totals, evidence references) rather than unbounded lists of records.
- **Conversation history:** Grows across turns; relevance-based selection (Section 15) bounds it for follow-ups.
- **Repeated tool calls:** Each tool call adds a result to context, so a looping model directly increases token use; bounded tool calls (Section 14) are the primary control.
- **Model latency:** Per-call latency compounds across a multi-step trajectory; the spending-change scenario requires several calls per request.
- **Model cost:** Directly proportional to input tokens, output tokens, and number of calls; relevant only when a paid provider is selected.

## 18.2 No premature optimization

These considerations are recorded so the first slice is architected with bounded context in mind, but no context-management algorithm, size limit, or cost budget is fixed speculatively. Context selection, serialization, and limits should evolve based on actual measurements (token counts, result sizes, latency, cost) recorded during the first slice's evaluation (Section 21). Concrete token/cost limits remain TBD (Section 26).

# 19. Security and Privacy

## 19.1 LLM-specific privacy boundary

Because the LLM may be an external service, sending data to a model is itself a data exposure and must be governed by a privacy boundary:

- **Minimize sensitive financial data sent to a model:** Prefer structured analytical results over raw records; exclude descriptions and identifiers where a result can be expressed without them.
- **Avoid unnecessary raw transaction exposure:** Raw transactions are not included in prompts by default (Section 6.2). Any future case that requires raw records must be justified and evaluated consciously.
- **API credential handling:** Credentials, when a provider is chosen, come from local configuration or environment variables and are never hard-coded or committed (consistent with `docs/06_implementation.md`, section 20). No credentials are introduced in this phase.
- **Logging restrictions:** Logs and trajectory records must not contain raw transaction data, credentials, or unnecessary sensitive context. Observability (Section 20) is privacy-aware.
- **Prompt/output privacy:** Both what is sent to the model and what the model produces are treated as sensitive; neither is logged verbatim where avoidable.
- **Retention considerations:** What is retained, where, and for how long must be decided before an external provider is used.
- **Third-party model providers:** Do not assume any specific provider's privacy policy. Whether an external provider use is acceptable for this data at all is a decision to be made separately, with the option to prefer local model execution remaining open.

## 19.2 Relationship to the existing privacy stance

The system already keeps data local-first, treats transaction data as private, and excludes raw/private data from committed artifacts (`.gitignore`, `docs/06_implementation.md`). The LLM integration does not weaken that stance: context minimization and minimum-disclosure apply to every call. The exact privacy and retention policy for external providers is TBD (Section 26).
# 20. Observability

## 20.1 What should be observable about LLM execution

The following should be recorded for every model-powered execution, mirroring and extending the trajectory records already defined in `runtime/state.py` and the observability requirements in `docs/04_agent_design.md` (section 22):

- **Execution ID:** Identifies one request execution.
- **Model/provider identity:** Which model and provider produced each decision, including version metadata where available.
- **Request/interaction stage:** The lifecycle stage (understand, plan, act, observe, verify, replan, respond) associated with each model call.
- **Tool calls:** The validated tool name and a summary of its arguments.
- **Tool results:** Structured result metadata (status, totals where small, evidence references), not raw transaction dumps.
- **Verification results:** Trust classification and check details for each verified tool result.
- **Latency:** Time per model call and total execution time.
- **Errors:** Model errors, rejected tool calls, parser failures, timeouts, and verification failures, with their classification.
- **Token usage where available:** Input/output token counts per call when the provider reports them.
- **Termination reason:** Why execution stopped (task complete, max steps, max tool calls, error, clarification required, verification failed).

## 20.2 Privacy-aware logging

Observability records must respect the privacy boundary (Section 19): no raw transaction data, no credentials, no unnecessary sensitive context in logs or trajectory records. Tool results are logged at the level of structured metadata sufficient for debugging and evaluation without exposing financial detail beyond what is necessary. Exact log format, retention, and storage are TBD (Section 26).

# 21. Evaluation Implications

Introducing an LLM changes the evaluation problem. Following `docs/07_testing_and_evaluation.md`, evaluation must cover both the final response and the trajectory the agent took.

## 21.1 Final response evaluation

- **Correctness:** Do the reported numbers and scope match the verified analytical results?
- **Groundedness:** Are all financial claims traceable to observations and verification records in state?
- **Completeness:** Does the response answer the full request (all requested periods, dimensions, and the requested explanation)?
- **Clarity:** Is the response understandable and appropriately structured?
- **Unsupported claims:** Does the response avoid invented numbers, invented contributors, and unsupported causal claims?

## 21.2 Trajectory evaluation

- **Intent understanding:** Did the model interpret the request correctly (intent, periods, constraints)?
- **Tool selection:** Did the model choose appropriate tools for the intent?
- **Tool arguments:** Were the arguments correct and well-formed?
- **Unnecessary tool calls:** Did the model perform redundant or irrelevant work?
- **Missing evidence:** Did the model stop before gathering necessary evidence?
- **Replanning:** Did the model add or drop steps appropriately based on observations?
- **Verification handling:** Did the model respect trust classifications and failed verification?
- **Termination behavior:** Did the execution stop appropriately (task complete, or bounded and safe on failure)?

## 21.3 Method implications

The existing `AgentState` trajectory provides the substrate for both axes of evaluation. Two complementary test strategies are needed:

- **Deterministic model doubles:** For unit and integration tests, the `LLMClient` itself is replaced by scripted doubles returning known structured decisions, keeping tests deterministic and provider-free.
- **Evaluation corpus with a real model:** For realistic assessment, structured scenarios (including the spending-change explanation scenario) are run against a real model and scored on the two axes above.

Metrics, thresholds, evaluation dataset, and comparison method remain TBD (see `docs/07_testing_and_evaluation.md` section 32). The design goal is that adding an LLM does not reduce the existing rigorous, deterministic verification of calculations and evidence.
# 22. Initial LLM Integration Scope

## 22.1 The first model-powered vertical slice

The first real LLM-powered slice focuses on one scenario, the spending-change explanation:

> "Why did my September spending increase?"

This scenario is selected because it is the first supported request where genuine iterative agent behavior is valuable: the answer requires comparison first, and the need for category and merchant analysis depends on what the comparison shows.

The initial flow must demonstrate:

```text
LLM understanding
  -> LLM planning/tool selection
  -> deterministic analysis
  -> verification
  -> observation returned to LLM
  -> additional tool selection when evidence warrants it
  -> grounded final response
```

## 22.2 Explicit scope limits

- Only the spending-change explanation intent is model-powered in the first slice.
- Other supported intents continue to use the deterministic runtime path unchanged.
- The deterministic tools, verification, state, and trajectory recording are preserved and reused (they are the execution layer of the slice).
- No multi-agent, RAG, persistence, database, or orchestration framework is introduced.

## 22.3 Success criteria for the slice

The slice is successful when a request like the example produces a verified trajectory (comparison, followed by warranted category/merchant analysis) and a grounded response whose numbers match verified results, as measured by the evaluation approach in Section 21. This validates the boundaries defined in this document before any wider generalization is attempted.

# 23. Architecture Alternatives Considered

Four alternatives for the division of responsibility were considered.

## Option A - LLM only for response generation

Understanding, planning, and tool selection remain deterministic; the LLM only converts the final verified results into natural language.

- **Benefits:** Minimal nondeterminism; lowest risk; simplest to test and evaluate.
- **Drawbacks:** The system gains none of the natural-language flexibility or contextual interpretation that motivates an LLM; understanding and planning remain brittle; conversational follow-up remains weak.

## Option B - LLM for understanding and response

The LLM interprets the request and writes responses; deterministic planning and tool selection decide which tools run.

- **Benefits:** More robust request understanding and follow-up; deterministic tool selection preserves correctness.
- **Drawbacks:** Planning is still fixed; requests that need an adaptive investigation (such as spending-change explanation) cannot choose intermediate tools based on what they learn.

## Option C - LLM for understanding, planning, and tool selection

The LLM interprets the request, proposes plans, and selects the next tool; the runtime validates and executes deterministically and verifies results.

- **Benefits:** Flexible analysis and genuine iterative behavior; correctness protected by deterministic tools, verification, and runtime guardrails; trajectory remains inspectable and evaluable.
- **Drawbacks:** Introduces nondeterminism into which actions run, requiring validation, bounded loops, and trajectory evaluation. This is manageable given the small tool set and explicit guardrails.

## Option D - LLM controls most of the runtime

The model drives nearly all decisions, including direct interpretation of raw or filtered data.

- **Benefits:** Maximum flexibility and minimal separation of concerns.
- **Drawbacks:** Unreliable arithmetic and evidence interpretation, unsafe action potential, and hard-to-test behavior. This is not appropriate for a financial-analysis domain where numerical correctness and verification are requirements.

## 23.1 Comparison

| Option | Flexibility | Financial correctness | Complexity | Testability | Suitability now |
|---|---|---|---|---|---|
| A | Low | High (unchanged determinism) | Low | High | Limited agent value |
| B | Medium | High | Medium | Medium-High | Partial |
| C | High within supported scope | High when tools and verification remain authoritative | Medium | Medium-High | **Preferred** |
| D | Highest | At risk | High | Low | Not appropriate |

## 23.2 Recommendation

Option C is recommended: the LLM handles understanding, planning, and tool selection while deterministic tools and verification remain authoritative and the runtime remains the control boundary. This best matches the project philosophy of using reasoning where it adds value while keeping computation and evidence deterministic and verified.

# 24. Initial LLM Integration Decision

The current architectural decision is the recommendation above:

> The LLM will serve as the reasoning/orchestration layer for natural-language understanding, planning, tool selection, contextual interpretation, and grounded response generation. Deterministic analytical tools and verification remain authoritative for financial computation and evidence. The existing Agent Runtime remains the control boundary.

Consequences of this decision:

- The Model may propose intent, plans, tool calls, interpretations, and responses, but never computes, executes, bypasses verification, or mutates state directly.
- The runtime interfaces defined in this document (context construction, tool-calling contract, result contract, verification wiring, state interaction, guardrails) are the contracts the first slice implements.
- Provider, SDK, structured-output mechanism, and operational parameters remain TBD (Section 26).

This is a design-phase decision. It should be reflected in the decision log (`docs/09_decisions_and_changes.md`) when implementation begins and any detail changes should be recorded there.
# 25. Implementation Constraints

The following will **not** be introduced during the first LLM integration:

- **Multi-agent architecture:** The system remains a single agent with deterministic tools.
- **RAG:** No retrieval-augmented generation; relevant evidence is produced by the deterministic tools.
- **Vector database:** No vector storage or semantic search.
- **Persistent memory:** No durable conversation history or memory store.
- **Database:** No new storage layer.
- **Complex orchestration framework:** No LangChain, LangGraph, or similar frameworks; the runtime is the orchestrator.
- **Cloud deployment:** No hosted services or deployment infrastructure.
- **Frontend:** No user interface changes.
- **Arbitrary code execution:** The only execution path for the model is validated tool calls.
- **Direct financial APIs:** No connection to banking, payment, or external financial services.
- **Advanced autonomous behavior:** No open-ended autonomy; execution is bounded and step-validated.

These may be reconsidered later only if requirements and evaluation results justify them. This is consistent with the project's evidence-before-complexity principle and the existing decisions in `docs/09_decisions_and_changes.md`.

# 26. Open Questions / TBD

The following decisions are intentionally unresolved in this design phase. They should be resolved during implementation and evaluation rather than assumed in advance:

- **Model/provider:** Which model and provider, if any, will be used. Selection criteria (quality, cost, latency, privacy, local-execution feasibility) are also TBD.
- **Exact SDK/interface:** The concrete contract and serialization of the provider-neutral `LLMClient`.
- **Structured output mechanism:** How the model produces structured decisions (structured-output constraints, parsing, or another mechanism, if required).
- **Tool-call protocol:** The exact representation of tool definitions and calls through the interface.
- **Model selection criteria:** Formal criteria and how candidate models will be compared.
- **Context window strategy:** How context layers are selected, sized, serialized, and truncated.
- **Retry policy:** Which failures are retryable, how many retries, and backoff.
- **Timeout values:** Per-call and per-execution timeout budgets.
- **Model fallback strategy:** Whether/what fallback exists when the primary model or provider fails.
- **Token/cost limits:** Per-call, per-request, and optionally per-usage budgets, measured after real use.
- **Prompt versioning mechanism:** How instruction sets are versioned, identified, and compared.
- **Whether response generation should remain partially deterministic:** Whether numbers and scope stay runtime-formatted with the model supplying only interpretation.
- **Privacy/retention policy for external model providers:** Whether external provider use is acceptable for the data, what is transmitted, and what is retained.

These items remain open; implementing them speculatively would contradict the project's documented approach of deciding from evidence.

# 27. Handoff to Implementation

This document defines the architecture boundary between the deterministic agent runtime and a future LLM. The next implementation phase should:

1. define the provider-neutral LLM client interface;
2. select and configure an initial model/provider;
3. implement structured model interaction (context construction, structured decisions, error/timeout handling);
4. integrate LLM understanding, planning, and tool selection behind the validated tool-calling contract;
5. connect tool results and verification back to the model;
6. implement the first spending-change explanation trajectory ("Why did my September spending increase?");
7. preserve the existing deterministic tools and verification layer unchanged as the execution authority;
8. add comprehensive LLM/agent evaluation tests covering both final responses and trajectories (Section 21).

These items are **not** implemented in this phase. The deterministic runtime remains the working system until the first LLM slice is designed, implemented, and evaluated against the boundaries and guardrails defined here. When implementation begins, concrete decisions (Section 26) should be recorded in the decision log (`docs/09_decisions_and_changes.md`), and this document should be updated to reflect the implemented reality.