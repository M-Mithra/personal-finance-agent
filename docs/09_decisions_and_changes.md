# Engineering Decision Log

## 1. Purpose

This living log records important architectural, technical, data, agent, testing, deployment, operations, and scope decisions for the Personal Finance Agent.

Each record preserves the reasoning behind a decision so later changes can be understood rather than appearing arbitrary. The log should be updated when a significant decision is made, changed, or superseded. It should reference the detailed project document instead of duplicating it.

## 2. Decision Status

- **DECIDED** - Decision has been made and is currently accepted.
- **PROPOSED** - A possible decision is being considered but is not final.
- **SUPERSEDED** - An earlier decision was replaced by a later decision.
- **REVISIT** - The decision remains valid but should be reconsidered later.

## 3. Decision Record Format

Each decision record should contain:

- **Decision ID:** Stable identifier such as `DEC-001`.
- **Date:** Decision date, or `TBD` when unknown.
- **Area:** Scope, architecture, data, agent, implementation, testing, deployment, or operations.
- **Status:** One of the statuses above.
- **Decision:** The accepted choice or boundary.
- **Context / Problem:** Why the decision was needed.
- **Alternatives Considered:** Relevant alternatives, without reconstructing every design discussion.
- **Rationale:** Why the decision was selected.
- **Consequences:** Expected benefits, constraints, and follow-up work.
- **Related Documentation:** Documents that define the decision in more detail.

## 4. Initial Project Decisions

### DEC-001 - Project Focus

- **Date:** TBD
- **Area:** Scope
- **Status:** DECIDED
- **Decision:** Focus the project on personal transaction and spending analysis rather than tax, investment, banking, payments, credit, or other financial services.
- **Context / Problem:** The project needs a focused initial problem domain.
- **Alternatives Considered:** Broader personal-finance functionality.
- **Rationale:** Spending analysis is the established initial scope and supports a manageable investigation of grounded agentic behavior.
- **Consequences:** Out-of-scope financial domains are not MVP requirements.
- **Related Documentation:** `01_problem_and_objectives.md`, `02_requirements.md`

### DEC-002 - Agent Role

- **Date:** TBD
- **Area:** Agent
- **Status:** DECIDED
- **Decision:** The system uses an interpretation and analysis agent that understands user questions, determines required analysis, selects analytical capabilities, interprets results, verifies important results, and provides grounded explanations.
- **Context / Problem:** Static summaries alone do not address context-dependent spending questions.
- **Alternatives Considered:** A fixed reporting/dashboard system; a single conversational response without explicit analysis.
- **Rationale:** The agent is being investigated for flexible, context-dependent analysis while deterministic capabilities handle calculations.
- **Consequences:** Agent state, planning, actions, observations, verification, and response behavior must be testable.
- **Related Documentation:** `03_system_design.md`, `04_agent_design.md`

### DEC-003 - Deterministic Computation vs. LLM Reasoning

- **Date:** TBD
- **Area:** Architecture / Agent
- **Status:** DECIDED
- **Decision:** Use deterministic programmatic capabilities for arithmetic, filtering, aggregation, period calculations, and similar data processing where appropriate. Use intelligent reasoning primarily for request understanding, planning, interpretation, explanation, and conversation.
- **Context / Problem:** Free-form reasoning is not the preferred source of truth for numerical calculations.
- **Alternatives Considered:** LLM-only processing; routing all work through one mechanism.
- **Rationale:** Deterministic operations are easier to test, verify, and trace.
- **Consequences:** The agent must invoke analytical capabilities and must not silently recreate their numerical results.
- **Related Documentation:** `03_system_design.md`, `04_agent_design.md`, `06_implementation.md`

### DEC-004 - Verification as a First-Class Concern

- **Date:** TBD
- **Area:** Architecture / Testing
- **Status:** DECIDED
- **Decision:** Important analytical results must be validated and verified before being presented as reliable user-facing conclusions.
- **Context / Problem:** A returned value or fluent response is not sufficient evidence of correctness.
- **Alternatives Considered:** Trusting analytical output or generated responses without a separate verification path.
- **Rationale:** Verification is required for numerical correctness, groundedness, and safe failure behavior.
- **Consequences:** Verification has its own logical responsibility, implementation checks, and tests.
- **Related Documentation:** `02_requirements.md`, `03_system_design.md`, `06_implementation.md`, `07_testing_and_evaluation.md`

### DEC-005 - Evidence-Grounded Insights

- **Date:** TBD
- **Area:** Agent / Data
- **Status:** DECIDED
- **Decision:** Responses must distinguish computed facts, observations supported by transaction evidence, and interpretations or hypotheses. Unsupported assumptions must not be presented as facts.
- **Context / Problem:** Transaction data can support observations without establishing user motives or causes.
- **Alternatives Considered:** Free-form explanations without evidence or uncertainty boundaries.
- **Rationale:** Groundedness and traceability are core success criteria.
- **Consequences:** Analytical results need scope and evidence references, and response claims require grounding checks.
- **Related Documentation:** `04_agent_design.md`, `05_data_design.md`, `07_testing_and_evaluation.md`

### DEC-006 - Start Simple

- **Date:** TBD
- **Area:** Architecture / Implementation
- **Status:** DECIDED
- **Decision:** Keep the initial implementation intentionally simple. Do not introduce multi-agent architecture, databases, RAG, vector databases, Docker, complex orchestration frameworks, or production-scale infrastructure unless a later requirement provides a clear reason.
- **Context / Problem:** Premature infrastructure would obscure the core learning and evaluation goals.
- **Alternatives Considered:** Building future infrastructure during the MVP.
- **Rationale:** The project philosophy is to build a working vertical slice and add complexity only when justified.
- **Consequences:** The MVP favors one local modular application, in-memory state, local/sample data, deterministic tools, and simple observability.
- **Related Documentation:** `01_problem_and_objectives.md`, `03_system_design.md`, `06_implementation.md`, `08_deployment_and_operations.md`

### DEC-007 - Documentation as an Engineering Artifact

- **Date:** TBD
- **Area:** Process
- **Status:** DECIDED
- **Decision:** Maintain problem, requirements, design, implementation, testing, operations, and decision documentation throughout development.
- **Context / Problem:** Important reasoning should remain visible as the system evolves.
- **Alternatives Considered:** Documenting decisions only after implementation.
- **Rationale:** The project treats documentation as part of the engineering record.
- **Consequences:** Significant changes should update the relevant document and this log.
- **Related Documentation:** `01_problem_and_objectives.md` through `08_deployment_and_operations.md`

### DEC-008 - Scope Boundary

- **Date:** TBD
- **Area:** Safety / Scope
- **Status:** DECIDED
- **Decision:** The system does not perform banking operations, payments or transfers, tax filing or advice, investment management, loan or credit decisions, financial-product recommendations, automated movement of money, or autonomous financial decisions.
- **Context / Problem:** The initial system is for analysis and insight, not financial action or regulated advice.
- **Alternatives Considered:** Acting on user finances or expanding into broader financial services.
- **Rationale:** These boundaries are explicit in the initial requirements and scope.
- **Consequences:** Such requests must be declined, bounded, or identified as unsupported.
- **Related Documentation:** `01_problem_and_objectives.md`, `02_requirements.md`, `04_agent_design.md`

### DEC-009 - Evaluation-Driven Development

- **Date:** TBD
- **Area:** Testing / Evaluation
- **Status:** DECIDED
- **Decision:** Testing and evaluation are core engineering activities. Evaluation covers software correctness and agent quality, including analytical correctness, agent behavior, groundedness, fabrication avoidance, tool use, verification, conversation, and failure recovery.
- **Context / Problem:** A successful demo does not establish reliability.
- **Alternatives Considered:** Informal demonstration or final-response inspection alone.
- **Rationale:** The project must produce evidence that it satisfies its requirements.
- **Consequences:** Deterministic tests, evaluation cases, trajectory inspection, regression checks, and failure analysis are part of the lifecycle.
- **Related Documentation:** `06_implementation.md`, `07_testing_and_evaluation.md`

### DEC-010 - Extensible Architecture

- **Date:** TBD
- **Area:** Architecture
- **Status:** DECIDED
- **Decision:** Keep the initial architecture simple and understandable while preserving clean boundaries for future analytical capabilities, richer interfaces, persistent storage, external integrations, deployment infrastructure, and additional agents.
- **Context / Problem:** The MVP should not implement speculative complexity but should avoid making future change unnecessarily difficult.
- **Alternatives Considered:** A fixed architecture with no extension boundaries; premature implementation of future infrastructure.
- **Rationale:** Logical boundaries support future evolution without requiring those capabilities now.
- **Consequences:** Future additions must be justified by requirements and fit the established data, agent, analysis, verification, and observability boundaries.
- **Related Documentation:** `03_system_design.md`, `05_data_design.md`, `06_implementation.md`, `08_deployment_and_operations.md`

### DEC-011 - Deterministic Foundation Slice Before Any Agent Code

- **Date:** 2026-08-09
- **Area:** Implementation / Scope
- **Status:** DECIDED
- **Decision:** The first implementation slice is a pure standard-library deterministic foundation: canonical transaction model, CSV loading and validation, normalization, five baseline analytical capabilities, deterministic verification, and `unittest` coverage. No LLM, agent framework, database, API, UI, or container is part of this slice.
- **Context / Problem:** The agent layer needs reliable tools and structured results to reason over; building reasoning before verified deterministic capabilities would violate the established "deterministic computation for deterministic tasks" and "start simple" principles.
- **Alternatives Considered:** Starting with an LLM-driven prototype; adopting an agent framework or data-processing library for the first slice.
- **Rationale:** A small, fully tested deterministic core can be verified independently and later exposed to the agent as tools without redesign.
- **Consequences:** `tools.py`, `agent.py`, `responses.py`, `config.py`, and `observability.py` remain unimplemented until their slices; the foundation must keep its module boundaries stable as the agent layer arrives.
- **Related Documentation:** `06_implementation.md` (sections 3, 4, 19, 22), `04_agent_design.md`

### DEC-012 - Money and Canonical Transaction Semantics

- **Date:** 2026-08-09
- **Area:** Data
- **Status:** DECIDED
- **Decision:** Monetary amounts are `Decimal` values stored as absolute magnitude with `direction` as a separate `Direction` `StrEnum` (`expense`, `income`, `transfer`, `refund`, `unresolved`); dates are `datetime.date`; the canonical transaction and all analytical results are frozen dataclasses; percentage values are quantized with `ROUND_HALF_UP`; aggregation never mixes currencies and returns an explicit error status when a period spans multiple currencies.
- **Context / Problem:** Binary floating-point arithmetic is inappropriate for money, and sign-encoded amounts make spending rules ambiguous.
- **Alternatives Considered:** Signed float or integer-cent amounts; plain dictionaries as analytical results.
- **Rationale:** Matches the data design's amount/direction separation, keeps arithmetic exact and auditable, and gives results explicit types and evidence.
- **Consequences:** Spending is defined by direction filters (default `expense` only) rather than by amount sign; every analytical result carries an explicit currency and status.
- **Related Documentation:** `05_data_design.md`, `06_implementation.md` (section 10)

### DEC-013 - Verification by Independent Deterministic Recomputation

- **Date:** 2026-08-09
- **Area:** Testing / Verification
- **Status:** DECIDED
- **Decision:** Verification re-derives analytical results with independent deterministic logic and compares them to the claimed results, returning a structured verdict (`passed`, `failed`, or `inconclusive`) with per-check diagnostics; no LLM is involved.
- **Context / Problem:** A result checked by the same code path that produced it cannot catch implementation errors, and a future agent must distinguish "verified", "wrong", and "cannot tell".
- **Alternatives Considered:** LLM-based self-checking; verifying only by re-running the same analytics functions.
- **Rationale:** Independent recomputation detects tampering, inconsistent evidence references, and reconciliation failures deterministically and is fully unit-testable.
- **Consequences:** New analytical capabilities should ship with matching verification functions and failure-path tests; verification results are structured for later agent consumption.
- **Related Documentation:** `06_implementation.md` (section 16), `07_testing_and_evaluation.md`

### DEC-014 - Committed Synthetic Sample Data

- **Date:** 2026-08-09
- **Area:** Data / Privacy
- **Status:** DECIDED
- **Decision:** Development uses a committed, clearly synthetic CSV dataset (`data/sample/transactions.csv`) generated by `synthetic.py`, covering August and September with everyday and a few larger transactions; no real personal financial data is committed.
- **Context / Problem:** Deterministic tests and month-to-month analysis need stable, varied, privacy-safe data.
- **Alternatives Considered:** Generating data only inside tests; using anonymized real data.
- **Rationale:** A stable committed fixture makes analytics, verification, and future evaluation reproducible; generation code keeps the dataset auditable and regenerable.
- **Consequences:** The dataset must remain clearly synthetic; real transaction data must never be committed (see `.gitignore` and `06_implementation.md` section 20).
- **Related Documentation:** `05_data_design.md`, `06_implementation.md` (section 10), `08_deployment_and_operations.md`

### DEC-015 - Deterministic Runtime Scaffold Before Any LLM

- **Date:** 2026-08-09
- **Area:** Agent / Implementation
- **Status:** DECIDED
- **Decision:** The initial agent runtime is a deterministic scaffold implementing the explicit lifecycle (Understand → Plan → Execute → Observe → Validate → Update State → Replan → Verify → Respond) without any LLM. Request understanding uses transparent keyword matching; planning uses deterministic action selection; response generation reads only from verified structured evidence.
- **Context / Problem:** Building reasoning before establishing the runtime lifecycle and interfaces would risk redesigning the entire system when an LLM is introduced.
- **Alternatives Considered:** Starting with an LLM-driven prototype; using an agent framework.
- **Rationale:** A deterministic runtime scaffold makes every lifecycle stage, state field, and trajectory step explicit and testable; a future LLM can replace the deterministic understanding/planning modules without redesigning the runtime loop, tool interface, or response generator.
- **Consequences:** The runtime must keep its module boundaries stable; the understanding and planning boundaries must remain provider-neutral.
- **Related Documentation:** `04_agent_design.md` (sections 6-12), `06_implementation.md` (sections 6, 7, 22)
### DEC-016 - Explicit Agent State as a Single Inspectable Value

- **Date:** 2026-08-09
- **Area:** Agent / State
- **Status:** DECIDED
- **Decision:** Agent state is a single mutable dataclass (`AgentState`) that records the original request, interpreted intent, plan, pending/completed actions, observations, verification records, errors, assumptions, an append-only trajectory (each entry tagged with a lifecycle stage and UTC timestamp), and the final response. No global mutable state: each request constructs a fresh `AgentState` mutated only through the runtime loop.
- **Context / Problem:** Evaluation needs to inspect not just the final answer but whether the agent took the correct actions to reach it; log-only records are insufficient.
- **Alternatives Considered:** Log-based reconstruction; distributed state across modules.
- **Rationale:** A single verbose state object makes every stage inspectable after execution and supports future trajectory-based evaluation.
- **Consequences:** `AgentState` is intentionally large; it must remain serializable-friendly (plain dataclasses/enums/strings).
- **Related Documentation:** `04_agent_design.md` (section 8), `06_implementation.md` (section 7)

### DEC-017 - Tool/Action Interface Wrapping Analytical Capabilities

- **Date:** 2026-08-09
- **Area:** Agent / Tools
- **Status:** DECIDED
- **Decision:** The agent runtime never calls analytical functions directly. Instead it invokes them through a controlled tool/action interface (`runtime/tools.py`) that dispatches by tool name to the matching capability in `analytics.py`. Each tool has a clear name, a validated input contract (Period + transaction sequence + optional currency), and a deterministic output structure (an analytical result dataclass). The five initial tools map 1:1 to the five analytical capabilities.
- **Context / Problem:** Embedding calculations in the reasoning path would make the runtime untestable and tightly coupled to analytics internals.
- **Alternatives Considered:** Calling analytics directly from the agent; embedding logic in the planner.
- **Rationale:** A dispatch boundary keeps the runtime independent of analytics implementations and makes tool selection observable in the trajectory.
- **Consequences:** Adding a new analytical capability requires registering a corresponding tool; tool contracts must remain stable.
- **Related Documentation:** `06_implementation.md` (sections 5, 6.1)

### DEC-018 - Bounded Replanning Without Open-Ended Loops

- **Date:** 2026-08-09
- **Area:** Agent / Replanning
- **Status:** DECIDED
- **Decision:** Replanning is bounded: after executing an action, the runtime inspects observations and decides whether follow-up actions are needed. For the spending-change explanation intent, after observing a meaningful spending increase, the runtime ensures category and merchant analyses are planned for the later period. No open-ended loop is introduced.
- **Context / Problem:** The project needs to demonstrate iterative agent behavior without introducing unbounded or unpredictable loops.
- **Alternatives Considered:** Open-ended replanning loops; multi-agent collaboration.
- **Rationale:** Bounded follow-up keeps execution deterministic, inspectable, and testable while still demonstrating the core replanning concept.
- **Consequences:** Replanning only applies to intents that need follow-up; simple intents execute a single action and respond.
- **Related Documentation:** `04_agent_design.md` (section 10), `06_implementation.md` (section 6.1)

### DEC-019 - Provider-Neutral LLM Abstraction Before Provider Selection

- **Date:** 2026-08-09
- **Area:** Agent / LLM
- **Status:** DECIDED
- **Decision:** Implement the provider-neutral LLM abstraction (package `llm/`) before selecting any provider: the `LLMClient` interface (`client.py`), structured provider-neutral response types (`types.py`: `ToolCall`, `ModelResponse`, `LLMRequest`), model-facing tool definitions (`tool_definitions.py`), a typed error vocabulary (`errors.py`), and a deterministic scripted `FakeLLMClient` (`fake.py`). The Agent Runtime exposes an injectable `llm_client` boundary (`run(..., llm_client=...)` and `Agent(transactions, llm_client=...)`) that records the model identity on `AgentState` without changing the deterministic lifecycle. No SDK, credentials, prompt, or model call is introduced.
- **Context / Problem:** The runtime must not depend on any provider SDK, and the deterministic system must keep working while the model-powered slice is designed.
- **Alternatives Considered:** Selecting a provider first; embedding model logic in the `Agent` class; adding LangChain/LangGraph for abstraction.
- **Rationale:** A provider-neutral interface plus deterministic fake keeps all existing tests deterministic, lets defensive behavior be tested, and preserves the design's provider-neutral boundary (DEC-015, `docs/10_llm_integration_design.md` section 16).
- **Consequences:** The LLM proposes, the runtime validates/executes/verifies. Full model-powered execution is the next slice and is not implemented here.
- **Related Documentation:** `docs/10_llm_integration_design.md` (sections 7, 16), `docs/06_implementation.md` (sections 4, 5, Slice 5)

### DEC-020 - Local LLM Experiment: Ollama + Qwen3 4B

- **Date:** 2026-08-09
- **Area:** Agent / LLM / Local Inference
- **Status:** EXPERIMENTAL — not a permanent commitment
- **Decision:** Investigate Ollama running Qwen3 4B locally as the first experimental LLM backend for the Personal Finance Agent. This is explicitly an experiment: neither Ollama nor Qwen3 4B is a permanent architectural commitment. The provider-neutral ``LLMClient`` remains the boundary; Ollama/Qwen3 is one implementation behind that boundary. No Ollama SDK, model download, API call, or inference code is introduced in this documentation phase.
- **Context / Problem:** Before committing to a paid hosted API, the project wants to evaluate local inference for cost-free experimentation, privacy/data-locality, unrestricted iteration, and learning. Qwen3 4B is small enough to investigate on the target hardware (Apple Silicon M2, 8 GB unified memory) while still offering modern reasoning/instruction-following capabilities. Tool-calling and structured-output suitability must be evaluated empirically; model quality and resource usage are TBD until measured.
- **Alternatives Considered:** Hosted frontier API (deferred — introduces cost and external data transmission); larger local model (riskier on 8 GB hardware — consider after initial feasibility is established); smaller local model (less reasoning capacity); different local runtime (Ollama chosen initially for workflow simplicity).
- **Rationale:** Local inference lets us learn agent engineering against a real model without API costs or rate limits. Qwen3 4B is a reasonable first feasibility probe. The ``LLMClient`` boundary protects the agent from provider/runtime lock-in, so a failed experiment does not invalidate the architecture (DEC-015, DEC-019).
- **Consequences:** The experiment may conclude that Qwen3 4B is adequate, that a different local model/runtime is needed, or that a hosted model is materially better. The agent runtime, tools, and verification architecture remain unchanged regardless of the outcome. All evaluation cases, success criteria, and failure criteria are defined in `docs/11_local_llm_integration.md` before implementation begins.
- **Related Documentation:** `docs/10_llm_integration_design.md` (sections 16–26), `docs/11_local_llm_integration.md` (all sections)

### DEC-021 - Provisional Local Model Selection: Qwen3 1.7B

- **Date:** 2026-08-09
- **Area:** Local Inference / Model Selection
- **Status:** PROVISIONAL
- **Decision:** Qwen3 1.7B is provisionally selected as the first local model for MVP integration through the provider-neutral `LLMClient`. Ollama is the initial experimental inference runtime. This is a provisional implementation choice, not a permanent model selection.
- **Context / Problem:** Initial feasibility experiments compared Qwen3 1.7B and Qwen3 4B on the M2/8 GB development machine (see "Local LLM Experiment Results" in `docs/11_local_llm_integration.md`).
- **Alternatives Considered:** Qwen3 4B (stronger reasoning/grounding but substantially higher latency — approximately 40 seconds for simple tool-calling tasks and approximately 87 seconds for the tested grounded response); other local models; larger local model; hosted model.
- **Rationale:** Qwen3 4B demonstrated stronger reasoning and grounding behavior but showed substantially higher latency. Qwen3 1.7B demonstrated acceptable behavior on the tested cases with substantially lower latency (approximately 4–12 seconds on several agent-oriented tests). Tool calling works when contracts are explicit. Deterministic runtime safeguards compensate for known weaknesses.
- **Important qualification:** Qwen3 1.7B demonstrated sensitivity to tool-contract clarity and produced incorrect tool-argument ordering under weaker instructions. Therefore runtime-side validation, deterministic tools, and independent verification remain mandatory.
- **Consequences:** First Ollama-backed `LLMClient` implementation will target Qwen3 1.7B. Tool definitions must be explicit. Runtime validation remains authoritative. Qwen3 4B remains a benchmark/reference model. Model selection can be revisited after integration-level evaluation.
- **Related Documentation:** `docs/10_llm_integration_design.md`, `docs/11_local_llm_integration.md`, `docs/06_implementation.md`, `docs/07_testing_and_evaluation.md`

### DEC-022 - Ollama-Backed LLM Provider Adapter

- **Date:** 2026-08-09
- **Area:** Agent / LLM / Implementation
- **Status:** DECIDED
- **Decision:** Implement the first concrete `LLMClient` as `OllamaLLMClient` in `src/personal_finance_agent/llm/ollama.py`, adapting the provider-neutral interface to Ollama's local HTTP API (`POST /api/chat`). The adapter uses stdlib HTTP only (`urllib.request`, `json`, `socket`); no SDK dependency. It is non-streaming initially (`stream: false`). Model, base URL, timeout, and generation options are configurable. Provider/transport failures are mapped to the existing provider-neutral error hierarchy. JSON format is request-dependent rather than unconditional. The adapter remains behind the provider-neutral `LLMClient`; the deterministic runtime remains the control boundary.
- **Context / Problem:** The provider-neutral `LLMClient` abstraction (DEC-019) is complete but had no real provider implementation. To run the agent against a real model, a concrete adapter is needed. Ollama was chosen as the first experimental runtime (DEC-020) and Qwen3 1.7B as the provisional first model (DEC-021).
- **Alternatives Considered:** Using the official Ollama Python SDK (rejected — adds a dependency for no functional benefit; stdlib HTTP is sufficient for the initial non-streaming use case); streaming support (deferred — adds complexity not needed for the initial trajectory); unconditional JSON format (rejected — couples the adapter to JSON mode unnecessarily; tool calls use Ollama's native `tools` mechanism).
- **Rationale:** A stdlib-only adapter keeps the project dependency-light while making the `LLMClient` abstraction executable against a real model. Keeping it behind the provider-neutral interface preserves the ability to swap providers later. Non-streaming simplifies the initial implementation. Configurable model/URL/timeout allow experimentation without code changes.
- **Consequences:** The agent can now be run against a real local model once Ollama is installed and the model is pulled. The adapter does not execute tools, calculate results, or bypass verification — those responsibilities remain with the deterministic runtime. Future providers can be added as additional `LLMClient` implementations without touching the runtime.
- **Related Documentation:** `docs/10_llm_integration_design.md` (sections 7, 16), `docs/11_local_llm_integration.md`, `docs/06_implementation.md` (Slice 6)

## 5. Decisions by Engineering Area

| Area | Current Status |
|---|---|
| Problem Definition | Decided |
| Scope | Decided |
| Requirements | Decided at initial level |
| System Architecture | Initial design decided |
| Agent Architecture | Initial single-agent design decided |
| Data Model | Initial logical model decided |
| Analytical Tools | First five deterministic capabilities implemented within the established boundaries |
| Agent Runtime | Deterministic runtime scaffold implemented (lifecycle, state, understanding, planning, tools, replanning, response) |
| LLM Abstraction | Provider-neutral interface and FakeLLMClient implemented; no provider selected |
| LLM Provider Adapter | First concrete adapter (`OllamaLLMClient`) implemented behind `LLMClient`; stdlib HTTP only |
| Local Inference | Feasibility experiments complete (Ollama 0.33.3, Qwen3 4B + 1.7B on M2/8 GB); Qwen3 1.7B provisionally selected for MVP |
| LLM / Model Selection | PROVISIONAL — Qwen3 1.7B (not permanent) |
| Memory | OPEN/TBD; persistent memory not required initially |
| RAG | OPEN/TBD; not required initially unless justified |
| Database | OPEN/TBD; not required initially |
| External APIs | OPEN/TBD |
| User Interface | OPEN/TBD |
| Testing Strategy | Initial strategy decided |
| Evaluation Strategy | Initial strategy decided |
| Observability | Initial simple strategy decided |
| Deployment | Initial local-first approach decided |
| Containerization | Future consideration; not required initially |
| Security / Privacy | Initial principles decided; implementation TBD |
| Multi-Agent Architecture | Future consideration; not part of the MVP |

TBD items are not decisions. They remain open until a later requirement, implementation result, or evaluation establishes a justified choice.

## 6. Superseded Decisions

No superseded decisions yet.

## 7. Change Log

| Date | Change | Reason | Related Decision |
|---|---|---|---|
| TBD | Project documentation and architecture established as the initial baseline. | Establish the starting engineering record. | DEC-001 through DEC-010 |
| 2026-08-09 | Deterministic foundation slice implemented: canonical transaction model, CSV loading and validation, normalization, five analytical capabilities, deterministic verification, synthetic dataset, and 84 unit tests. | Provide verified deterministic capabilities before any agent development. | DEC-011 through DEC-014 |
| 2026-08-09 | Deterministic agent runtime implemented: explicit lifecycle state (`runtime/state.py`), deterministic understanding (`runtime/understanding.py`), planning (`runtime/planning.py`), tool/action interface (`runtime/tools.py`), verification wiring (`runtime/checks.py`), bounded replanning (`runtime/replanning.py`), grounded response generation (`runtime/response.py`), and the runtime loop (`runtime/agent.py`). | Establish the agent lifecycle, interfaces, and state representation before any LLM is introduced. | DEC-015 through DEC-018 |
| 2026-08-09 | Provider-neutral LLM abstraction implemented: `llm/client.py` (`LLMClient` interface and response validation), `llm/types.py` (structured response types), `llm/tool_definitions.py` (model-facing tool metadata), `llm/errors.py` (typed failure vocabulary), `llm/fake.py` (deterministic `FakeLLMClient`), and an injectable `llm_client` boundary on `run()` and `Agent`. | Establish the LLM boundary before any provider selection, keeping the deterministic runtime authoritative and unchanged. | DEC-019 |
| 2026-08-09 | Local LLM experiment designed: Ollama + Qwen3 4B proposed as the first experimental backend; documented in `docs/11_local_llm_integration.md`. No runtime, SDK, model download, or inference code introduced. | Evaluate local inference before committing to a paid hosted API; preserve the provider-neutral `LLMClient` boundary. | DEC-020 |
| 2026-08-09 | Local LLM feasibility experiments completed on Apple M2 (8 GB) with Ollama 0.33.3, comparing Qwen3 4B and Qwen3 1.7B. Qwen3 1.7B provisionally selected as the first MVP model (DEC-021); Qwen3 4B retained as evaluation baseline. | Empirical results favored 1.7B for latency on constrained hardware while 4B showed stronger reasoning; provider-neutral `LLMClient` boundary preserved. | DEC-021 |
| 2026-08-09 | First concrete provider adapter implemented: `OllamaLLMClient` (`llm/ollama.py`) adapts the provider-neutral `LLMClient` to Ollama's local HTTP API using stdlib only (no SDK); non-streaming, configurable model/URL/timeout, request-dependent JSON format, provider errors mapped to the existing error hierarchy (DEC-022). | Make the provider-neutral abstraction executable against a real model while keeping the project dependency-light. | DEC-022 |

## 8. Future Decision Areas

The following areas will require decisions as implementation and evaluation progress:

- Concrete transaction schema (resolved for the current slice by DEC-012; the final user-facing input contract remains open).
- Transaction categorization approach.
- Analytical functions and supported operation set.
- Anomaly or unusual-activity detection approach.
- LLM/model selection.
- Prompt and instruction design.
- Tool-calling mechanism.
- State implementation.
- Conversation handling and persistence.
- Evaluation dataset.
- Evaluation metrics and thresholds.
- Observability implementation.
- Security implementation.
- Deployment target.
- User interface.
- Persistence and retention.
- External integrations.
- Possible multi-agent evolution.

These are decision areas, not predetermined solutions.

## 9. Decision-Making Principles

1. Solve the actual problem before adding complexity.
2. Prefer deterministic computation for deterministic tasks.
3. Use agentic reasoning where it provides genuine value.
4. Keep important outputs verifiable.
5. Prefer evidence over unsupported assumptions.
6. Make architecture understandable before making it sophisticated.
7. Introduce infrastructure only when justified by requirements.
8. Evaluate before optimizing.
9. Record why important decisions were made.
10. Preserve future extensibility without prematurely implementing future complexity.

## 10. How This Document Will Evolve

This is a living document. When a significant project decision changes:

1. Add a new decision record with a stable ID.
2. Explain the context and alternatives.
3. Record the rationale and consequences.
4. Link the relevant design or implementation documentation.
5. Mark the previous decision as **SUPERSEDED** when applicable.
6. Update the change log.

Project history should not be rewritten silently. A changed decision should preserve what changed and why.

## 11. Open Decision Questions

- Which exact transaction schema and input format will the MVP support?
- Which categorization approach will be implemented?
- Which analytical functions belong in the first working vertical slice?
- How will unusual and recurring spending be defined?
- Which model/provider, if any, will support request understanding and response generation?
- How will prompts and tool interaction be organized?
- What state and conversation handling will be implemented?
- What evaluation dataset, metrics, thresholds, and human rubric will be used?
- What observability implementation is appropriate beyond simple local logging?
- Is persistent storage required after the MVP workflow is evaluated?
- What interface and deployment target should be selected later?
- What security, privacy, retention, and external-integration controls will be required?
- Would a multi-agent design ever be justified by future requirements and evaluation?

These questions remain open and should not be resolved prematurely.

## 12. Current Baseline

The current documentation represents the initial project baseline: a simple, single-agent, transaction-analysis system with deterministic analytical capabilities, explicit verification, grounded responses, local-first implementation and operations, and evaluation-driven development. Implementation and evidence may change individual decisions as the project progresses; such changes should be recorded here rather than made silently.
