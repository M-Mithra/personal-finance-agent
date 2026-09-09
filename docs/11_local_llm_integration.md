# 11. Local LLM Integration

This document records the rationale, scope, constraints, architecture, and
evaluation plan for the first **local** LLM experiment.

It is an experiment/design document, not a claim that Qwen3 4B is already proven
suitable. Each section clearly distinguishes **decided**, **proposed**,
**experimental**, and **TBD** items.

---

## 11.1 Local LLM Integration Overview

The Personal Finance Agent is investigating **local inference** before
committing to a hosted API. The motivation is to learn agent engineering with
a real model while avoiding API costs during early experimentation, keeping
financial data local, and retaining full control over the inference
environment.

### Relationship to the existing architecture

The existing system already has a clean provider-neutral boundary:

* **Agent Runtime** (`src/personal_finance_agent/runtime/`) — the explicit
  lifecycle loop (understand, plan, execute, observe, verify, replan, respond).
* **LLMClient** (`src/personal_finance_agent/llm/client.py`) — the abstract
  application-level interface the runtime uses to interact with a model.
* **LLMRequest / ModelResponse / ToolCall** (`types.py`) — provider-neutral
  structures for context and model output.
* **FakeLLMClient** (`fake.py`) — a scripted deterministic client used in tests.

The local experiment adds one new implementation of `LLMClient`:

* **Local inference runtime** — Ollama (initial experimental choice).
* **Local model** — Qwen3 4B (initial experimental choice).

The agent runtime, deterministic analytical tools, verification layer, and
provider-neutral types are **unchanged**. Local inference is simply a new
`LLMClient` implementation behind the existing boundary.

### We are using a pretrained model

This project is **not** training an LLM. We are using an existing pretrained
model (Qwen3 4B) via an existing inference runtime (Ollama). The project's
learning goal is **agent engineering**, not model training.

### Why design before implementation

The LLM integration design (`docs/10_llm_integration_design.md`) defined the
architectural boundary. This document defines the **experimental implementation
path** behind that boundary. Designing first means:

* the agent architecture does not depend on Ollama or Qwen3;
* the experiment can be evaluated against clear criteria;
* failure of the experiment does not invalidate the agent architecture;
* alternatives remain open.

---

## 11.2 Motivation for Local Inference

Local inference is being investigated first for these reasons:

* **Cost avoidance during experimentation.** Early agent development involves
  many iterations, trajectory debugging, and evaluation runs. Paying per-token
  for every experiment slows learning and adds unpredictable cost.
* **Privacy / data locality.** Keeping financial data on-device during
  development reduces the surface area of external data transmission. This is
  a development-time benefit, not a claim that local inference is inherently
  more private in all configurations.
* **Unrestricted experimentation.** Local inference removes rate limits,
  availability windows, and provider-side content policies as confounding
  factors while learning agent behavior.
* **Learning local inference.** Understanding model sizing, quantization,
  context management, and local runtime behavior is itself valuable for agent
  engineering.
* **Provider independence.** A local-first experiment establishes a baseline
  that can later be compared against hosted models using the same agent
  runtime and evaluation cases.
* **Benchmark foundation.** The provider-neutral `LLMClient` means a future
  hosted model can be swapped in and compared against the local baseline
  without redesigning the agent.

Local inference is **not** claimed to be universally better. Hosted models may
ultimately provide superior quality, latency, or capability. The point is to
establish a local baseline first.

---

## 11.3 Hardware Constraints

The current development hardware is:

* **Machine:** Apple Silicon MacBook Air
* **Chip:** Apple M2
* **Unified memory:** 8 GB

### Why hardware matters for local inference

Running a local model requires loading model weights into memory and
maintaining a KV cache during generation. On an 8 GB machine, the following
all compete for the same unified memory pool:

* the operating system;
* the IDE and other development tools;
* the inference runtime (Ollama);
* the model weights;
* the KV cache and context storage;
* the agent runtime and dataset.

This constrains:

* **model size** — larger models may not fit or may leave insufficient room for
  context;
* **quantization** — lower-precision variants reduce memory usage at a
  potential quality cost;
* **context length** — longer contexts require more KV cache memory;
* **concurrent processes** — running other tools alongside the model may
  pressure memory.

### TBD performance characteristics

Detailed performance characteristics (exact RAM usage, tokens-per-second,
context-length headroom) are **TBD until measured** on this hardware. The
initial experiment is partly designed to produce these measurements.

---

## 11.4 Initial Runtime Choice: Ollama

**Ollama** is the **initial experimental** local inference runtime.

### Why Ollama is being considered

* **Local model execution.** Ollama runs models on the local machine rather
  than calling a remote API.
* **Simple developer workflow.** Model management (pull, serve, switch) is
  straightforward.
* **Local API boundary.** Ollama exposes a local HTTP API, which cleanly
  separates the inference runtime from our application.
* **Runtime/model separation.** Ollama supports multiple models, so the
  runtime and the model can be varied somewhat independently.
* **Compatibility with our architecture.** An Ollama-backed `LLMClient`
  implementation maps cleanly onto the existing `LLMRequest` / `ModelResponse`
  types.

### Ollama is an implementation choice, not a permanent dependency

**Ollama is an implementation choice for the experiment, not a permanent
architectural dependency.** The agent architecture depends on `LLMClient`, not
on Ollama. If Ollama proves unsuitable, another local runtime (or a hosted
provider) can be substituted behind the same interface without redesigning the
agent.

---

## 11.5 Initial Model Choice: Qwen3 4B

**Qwen3 4B** is the **first experimental** model.

### Why Qwen3 4B is being considered first

* **Small enough to investigate on constrained hardware.** A 4B-parameter
  model, especially in a quantized form, is a plausible starting point for an
  8 GB machine.
* **Relevant capabilities.** Qwen3 is designed for reasoning and
  instruction-following, which are relevant to agentic tool selection and
  grounded response generation.
* **Tool-calling / structured-output potential.** The Qwen family has
  tool-calling variants; whether the specific variant we use supports our
  structured `ToolCall` contract is **TBD until tested**.
* **Feasibility-first approach.** Starting with a smaller model lets us test
  the local inference pipeline, context construction, and tool-calling
  integration before attempting larger models.

### Qwen3 4B is not claimed to be the best local model

Whether Qwen3 4B is adequate for this agent is **an empirical question** the
experiment is designed to answer. Model quality, tool-calling reliability,
and resource usage must all be evaluated. Other models may prove more suitable.

---

## 11.6 Quantization Considerations

**Quantization** reduces the precision of model weights (e.g. from 16-bit
floating point to 4-bit integers). It matters because:

* **Model size.** A quantized 4B model can be roughly half (or less) the size
  of its full-precision equivalent.
* **Memory usage.** Smaller weights consume less RAM, leaving more room for
  the KV cache and other processes.
* **Inference performance.** Quantized models often generate tokens faster
  because they move less data.
* **Quality trade-offs.** Lower quantization can degrade reasoning,
  instruction-following, and tool-calling behavior. The acceptable trade-off
  is task-dependent and must be measured.

### Initial quantization approach

The initial experiment should use a **quantized variant appropriate to the
available hardware** (likely Q4 or Q5 for Qwen3 4B on an 8 GB machine). The
exact quantization level is **TBD until tested** and should be chosen based on
whether the model fits and whether quality remains acceptable for the
evaluation cases.

---

## 11.7 Local LLM Architecture

The local experiment fits into the existing architecture as follows:

### Request path

```text
User
  -> Agent Runtime
  -> LLMClient
  -> local LLM adapter (Ollama)
  -> Qwen3
```

### Response / tool path

```text
Qwen3
  -> structured model response
  -> LLMClient
  -> Agent Runtime
  -> validate tool call
  -> deterministic analytical tool
  -> independent verification
  -> Agent State
  -> LLM
  -> grounded response
```

### Control boundary

The **Agent Runtime remains the control boundary**. The LLM proposes actions;
the runtime validates and executes them. The LLM never directly executes
Python, never directly accesses or modifies `AgentState`, and never bypasses
verification.

---

## 11.8 Provider-Neutral Boundary

`LLMClient` is the **application-level abstraction**. Ollama/Qwen3 is only one
implementation.

Future implementations could include:

* another local runtime;
* another local model;
* a hosted provider (OpenAI, Anthropic, Gemini, etc.).

...without redesigning the agent. The agent runtime, tools, verification, and
state model depend only on `LLMClient` and the provider-neutral types
(`LLMRequest`, `ModelResponse`, `ToolCall`).

**Those alternatives are not implemented now.** This document concerns only the
Ollama/Qwen3 experiment.

---

## 11.9 Data and Privacy Boundary

The existing `LLMRequest` design already constrains what is sent to the model:

* **Raw transactions are not automatically included.** The request carries
  structured context (intent, tool definitions, observations, verification
  results, conversation context), not the raw transaction dataset.
* **Verified analytical results are preferred.** The model reasons over
  aggregated, verified evidence rather than raw records.
* **Context is minimized.** Only information relevant to the current reasoning
  step should be provided.
* **Local inference reduces external transmission.** With a local model, the
  data does not leave the machine during inference.
* **Local logging must still be privacy-aware.** Logs and recorded
  trajectories must avoid unnecessarily persisting sensitive financial data,
  even locally.

### Local inference does not automatically solve all privacy concerns

Local inference removes the external API transmission vector, but the model
may still retain information in memory, and local logs/recordings may still
capture sensitive data. Privacy is a system-wide concern, not solved solely by
choosing local inference.

---

## 11.10 First Experimental Use Case

The first real LLM-powered scenario is the **spending-change explanation**:

> "Why did my September spending increase?"

### Expected conceptual trajectory

1. Understand the request.
2. Determine the required investigation.
3. Call period comparison.
4. Verify the result.
5. Observe the result.
6. Decide whether additional evidence is needed.
7. Call category analysis and/or merchant analysis.
8. Verify the results.
9. Synthesize a grounded explanation.
10. Stop when sufficient evidence exists.

The exact trajectory is **model-dependent where appropriate**. The agent
runtime enforces tool boundaries, verification, and termination regardless of
what the model proposes.

This is the first scenario where genuine iterative agent behavior is valuable,
and the first place where the model's reasoning contribution is clearly
necessary beyond what deterministic logic provides.

---

## 11.11 Tool-Calling Requirements

The local model must demonstrate the following to be usable:

* **Correctly select available analytical tools** from the tool definitions.
* **Produce structured tool calls** compatible with the `ToolCall`
  representation (name + structured arguments).
* **Provide valid arguments** matching each tool's input contract.
* **Avoid nonexistent tools.** The runtime rejects unknown tools, but the model
  should not routinely propose them.
* **Avoid arbitrary code execution.** The model must work through the provided
  tools only.
* **Respond appropriately to tool results.** Use the structured observations
  and verification status to guide next steps.
* **Request additional evidence when needed.** Recognize when a single result
  is insufficient and select a follow-up tool.
* **Stop when sufficient evidence exists.** Avoid unnecessary additional tool
  calls once the investigation is complete.

---

## 11.12 Structured Output Requirements

Model output must be compatible with the provider-neutral `ModelResponse`
representation:

* A response is either a **tool-call request** or a **final response**.
* A tool call has a **name** and **structured arguments** (a dict), not
  natural-language text describing a call.
* The runtime **validates model responses independently** via
  `validate_model_response()`.

Where the inference runtime supports **structured output** (JSON mode,
function-calling, tool-use APIs), the implementation should prefer it over
natural-language parsing. The agent must not rely on parsing prose to extract
tool calls.

---

## 11.13 Verification Requirements

The verification interaction is unchanged from the existing architecture:

```text
Model
  -> tool request
  -> deterministic tool
  -> independent verification
  -> result returned to model
```

Key invariants:

* **The model cannot override verification.** A failed verification remains
  failed regardless of how confidently the model writes about the result.
* **A failed verification must not become an established financial fact.** The
  runtime treats failed-verification results as untrusted and surfaces them as
  such.
* **The model receives verification status** in the observation context and is
  expected to respond to it (e.g. by not citing an unverified number as fact).

---

## 11.14 Local Model Evaluation Plan

This section defines how we will determine whether Qwen3 4B is adequate for
the Personal Finance Agent. Evaluation must be empirical, not based on vague
"it feels good" assessment. Every item below should produce observable evidence.

The local model will be evaluated across these dimensions:

| Dimension | What is assessed |
|---|---|
| **A. Request understanding** | Does the model interpret the user's natural-language request and map it to the correct intent? |
| **B. Tool selection** | Does it select the correct analytical tool(s) for the request? |
| **C. Tool argument correctness** | Does it produce arguments that match each tool's input contract and pass validation? |
| **D. Multi-step planning** | Can it propose a sensible sequence of actions for a multi-step investigation? |
| **E. Replanning** | Does it add follow-up actions when initial evidence is insufficient? |
| **F. Evidence usage** | Does it reason over the structured observations returned by tools rather than ignoring them? |
| **G. Verification adherence** | Does it respect verification status and avoid treating failed-verification results as trusted facts? |
| **H. Grounded response generation** | Is the final response supported by verified evidence? Are numerical facts traceable to analytical results? |
| **I. Termination behavior** | Does it stop when sufficient evidence exists, rather than looping or stopping prematurely? |
| **J. Latency** | What is the per-request and end-to-end latency on the target hardware? |
| **K. Resource usage** | What memory/CPU footprint does the model have during inference on the target hardware? |
| **L. Reliability** | Is behavior deterministic/reproducible across repeated runs? Does it produce valid output consistently? |

Evaluation ties back to the requirements in `docs/02_requirements.md` and the
testing/evaluation plan in `docs/07_testing_and_evaluation.md`. The existing
synthetic dataset (`data/sample/transactions.csv`) provides the deterministic
baseline against which model-powered trajectories are compared.

Detailed evaluation results are **TBD** until the model is running locally.

---

## 11.15 Evaluation Cases

The initial benchmark uses six cases against the existing synthetic dataset. The
first model-powered trajectory should prioritize **case 5** (the spending-change
explanation). The remaining cases assess regressions and broader behavior.

| # | Case | Intent | Purpose |
|---|---|---|---|
| 1 | "How much did I spend in August?" | spending summary | Single-tool correctness |
| 2 | "What did I spend the most on?" | category analysis | Category reasoning |
| 3 | "Did I spend more in September than August?" | period comparison | Comparison + numerical reasoning |
| 4 | "Which merchants contributed most to September spending?" | merchant analysis | Contributor reasoning |
| 5 | "Why did my September spending increase?" | spending-change explanation | **Primary: multi-step iterative investigation** |
| 6 | "What were my biggest expenses recently?" | noteworthy transactions | Largest-expense reasoning |

Each case should produce:

* the model's trajectory (actions selected, arguments, observations);
* verification results for each analytical step;
* the final response;
* a pass/fail assessment against the expected trajectory and expected facts.

Expected trajectories and reference answers for each case are **TBD** until the
deterministic baseline is re-run against the current synthetic dataset to lock
exact expected numbers.

---

## 11.16 Success Criteria

A local model is considered **adequate** if it meets the following criteria.
Numerical thresholds are **TBD** until baseline measurements exist.

Qualitative criteria:

* produces **valid structured tool calls** in a format compatible with `ToolCall`;
* selects the **correct tool** for each evaluation case;
* provides **correct arguments** that pass runtime validation;
* does **not** propose unsupported/nonexistent tools in the evaluation cases;
* **respects verification status** (verified vs failed vs inconclusive);
* produces a **grounded final response** with no fabricated numerical facts;
* **completes** the spending-change investigation (case 5) within a bounded
  number of steps;

Quantitative/operational criteria (thresholds **TBD**):

* **Trajectory correctness**: the model's action sequence matches or acceptably
  approximates the reference trajectory;
* **Factuality**: all numerical claims in the final response match the
  deterministic analytical results;
* **No-unsupported-claims ratio**: the fraction of response claims that are
  traceable to verified evidence;
* **Step budget**: completes within N tool calls per request (N TBD);
* **Local latency**: acceptable per-request latency on target hardware (TBD);
* **Resource usage**: memory/CPU footprint that leaves the machine usable (TBD).

---

## 11.17 Failure Criteria

The local model should be considered **inadequate** if any of the following hold:

* it **frequently produces invalid tool calls** (malformed, wrong arguments,
  nonexistent tools) that fail runtime validation;
* it **cannot reliably provide valid tool arguments** matching the tool contract;
* it **fails to follow verification state**, e.g. cites a failed-verification
  result as an established fact;
* it **repeatedly loops** (requests the same tool with the same arguments, or
  cycles between tools) without making progress;
* it **fabricates financial numbers or explanations** unsupported by analytical
  evidence;
* it **cannot complete the spending-change investigation** (case 5) with a
  coherent, evidence-based explanation;
* **resource usage** makes local development impractical on the target hardware
  (e.g. the model cannot load, or renders the machine unusable).

**A model failing this experiment does not invalidate the agent architecture.**
It only means this model/runtime combination is not adequate, and the project
should test alternatives.

---

## 11.18 Benchmark and Comparison Strategy

The provider-neutral `LLMClient` boundary enables future comparison of different
model/runtime combinations using the **same agent runtime** and the **same
evaluation cases**.

Initial comparison candidates:

* Qwen3 4B + Ollama (the first experiment);
* other local models (e.g. other sizes, other families);
* other local inference runtimes (e.g. llama.cpp);
* hosted models (e.g. via OpenAI/Anthropic-compatible APIs).

Metrics to compare:

| Metric | Source |
|---|---|
| **Correctness** | Final response facts vs deterministic baseline |
| **Tool selection** | Actions chosen vs reference trajectory |
| **Trajectory quality** | Number of steps, unnecessary calls, replanning behavior |
| **Groundedness** | Fraction of claims traceable to verified evidence |
| **Latency** | Per-request and end-to-end latency on target hardware |
| **Resource usage** | Memory/CPU footprint during inference |
| **Cost** | Per-request cost (relevant for hosted providers) |

No comparison will be performed yet. The architecture supports it; the data
will come from running the evaluation cases against each candidate.

---

## 11.19 Alternatives Considered

The project is trying Qwen3 4B + Ollama first, but the alternatives below are
**not permanently rejected**.

| Alternative | Description | Why not first |
|---|---|---|
| **Hosted frontier API** (e.g. OpenAI, Anthropic) | Pay-per-token access to large models | Cost during experimentation; external data transmission; less control over runtime |
| **Larger local model** (e.g. 7B, 14B+) | Potentially better reasoning | Likely infeasible on the current hardware (8 GB unified memory) without aggressive quantization |
| **Smaller local model** (e.g. 1.5B, 3B) | Lower resource usage | May lack the reasoning/tool-calling quality needed for multi-step investigation |
| **Different local inference runtime** (e.g. llama.cpp) | Alternative local execution | Ollama has a simpler initial workflow and clear local API boundary |

**Qwen3 4B + Ollama** is being tried first because:

* 4B is a reasonable size to test feasibility on constrained hardware;
* Qwen3 has relevant reasoning/instruction-following capabilities;
* it allows testing tool-calling/structured-output suitability before committing
  to a larger model;
* if it fails, the next steps (smaller model, different model, hosted API) are
  still open.

---

## 11.20 Security and Privacy Considerations

Security and privacy concerns specific to the local LLM experiment:

* **Local model files.** Model weights are large binary artifacts. They should
  be stored locally and not committed to version control. Their provenance
  should be documented (source, tag, quantization).
* **Local API exposure.** Ollama exposes a local API. For the initial
  experiment this is development-only and should not be exposed beyond the
  local machine without re-evaluation.
* **Logs and recordings.** The agent records trajectory entries, observations,
  and (in future) model interactions. These logs may contain sensitive
  financial context and must be treated as privacy-sensitive. Do not commit
  logs containing financial data.
* **Transaction data.** Raw transactions are **not** automatically included in
  model context. The `LLMRequest` design provides structured, verified context
  (observations, verification status) rather than raw rows.
* **Model inputs/outputs.** Even with local inference, the content sent to the
  model and the content it returns should be considered potentially sensitive.
* **Future hosted credentials.** If a hosted provider is introduced later,
  API credentials must not be stored in code or committed to version control.

Local inference **reduces** external transmission concerns but does not
automatically solve all privacy and security concerns.

---

## 11.21 Operational Considerations

For the initial experiment, the operational posture is intentionally minimal:

* **Local development only.** No production deployment.
* **No Docker.** No containerization for the experiment.
* **No cloud infrastructure.** Everything runs on the local machine.
* **No persistent model-serving infrastructure.** Ollama is started/stopped
  as needed for development and evaluation.

Basic operational concerns to be aware of:

| Concern | Notes |
|---|---|
| **Model availability** | The selected Qwen3 model must be downloadable and loadable locally. |
| **Process lifecycle** | Ollama must be running before model calls; the client must handle "runtime unavailable" gracefully. |
| **Memory pressure** | On 8 GB unified memory, model size + KV cache + other processes may cause pressure. Monitor and record. |
| **Latency** | Local inference latency should be measured and recorded for the target hardware. |
| **Reproducibility** | Document runtime version, model tag, quantization, and relevant generation settings (see §11.22). |
| **Model/version tracking** | Pin the model artifact used for evaluation so results are reproducible. |
## 11.22 Version and Reproducibility

To make experiments reproducible, the following should eventually be recorded for each evaluated configuration:

| Item | Why |
|---|---|
| **Ollama runtime version** | Local runtime versions affect behavior and available features. |
| **Model name** | Identifies the base model (e.g. Qwen3). |
| **Model tag / quantization** | A 4B parameter model has multiple quantized variants with different size/quality trade-offs. |
| **Context length** | Affects how much context can be sent and how much history is usable. |
| **Generation settings** | Temperature, top-p, and similar settings affect determinism and quality. |
| **Hardware** | Model performance is hardware-dependent; the initial target is Apple Silicon M2 with 8 GB unified memory. |

Exact values for these items are TBD until the runtime is actually installed and measured.

## 11.23 Open Questions / TBD

The following remain unresolved and will be decided through experiment:

* Exact Ollama version
* Exact Qwen3 model tag and quantization level
* Context length to configure
* Generation parameters (temperature, top-p, etc.)
* Tool-calling mechanism (native tool calling vs. structured output vs. prompt-based extraction)
* Structured-output mechanism
* Local latency on the target hardware
* Memory usage under load
* Whether Qwen3 4B produces adequate tool-calling quality
* Whether Qwen3 4B produces adequate grounded-response quality
* Whether a larger local model is needed
* Whether another local runtime would be better
* Whether a hosted model eventually provides materially better results
* Retry policy and timeout values
* Fallback strategy if local inference is unavailable


---

## Local LLM Experiment Results

> **Status:** initial feasibility experiments complete. These are preliminary
> findings from a small set of manually constructed cases, not a statistically
> rigorous benchmark. Reported durations and token counts are approximate and
> were observed on the development hardware only.

### Experiment environment

| Item | Value |
|---|---|
| Machine | Apple Silicon MacBook Air |
| Chip | Apple M2 |
| Unified memory | 8 GB |
| Inference runtime | Ollama 0.33.3 |
| Acceleration | Apple Metal |
| Models tested | Qwen3 4B, Qwen3 1.7B |

---

### Qwen3 4B results

#### Experiment 1 — structured JSON

Prompted for structured JSON output.

* Structured JSON output succeeded.
* Required fields were produced correctly.
* No extra prose appeared in the model content.
* Approximate total duration: **6.88s**.
* Approximate `eval_count`: **148**.

#### Experiment 2 — tool calling with ambiguous month/year

User asked:

> "Why did my September spending increase compared with August?"

* Correct tool selected: `compare_period_spending`.
* Tool-call structure was valid.
* The model **invented the year 2023** when none was provided
  (temporal ambiguity / unsupported-assumption failure).
* Arguments: `period1 = 2023-08`, `period2 = 2023-09`.
* Approximate total duration: **41.9s**.
* Approximate `eval_count`: **912**.

#### Experiment 3 — tool calling with explicit dates

User asked:

> "Why did my September 2026 spending increase compared with August 2026?"

* Correct tool selected.
* Correct arguments: `period1 = 2026-08`, `period2 = 2026-09`.
* Approximate total duration: **40.1s**.
* Approximate `eval_count`: **771**.

#### Experiment 4 — additional analysis planning

Given verified totals plus `category_spending` and `compare_period_spending`
tools, the model was asked to plan next steps.

* Correctly recognized that total comparison alone was insufficient to explain
  the cause.
* Requested category-level analysis for both August and September.
* Correct tool selection and arguments.
* Approximate total duration: **31.4s**.
* Approximate `eval_count`: **668**.

#### Experiment 5 — grounded response generation

Given verified period totals and verified category totals:

* Correctly identified **Shopping** and **Entertainment** as the largest
  contributors.
* Correctly identified **Food** and **Transport** as smaller contributors.
* Correctly identified **Bills** and **Other** as unchanged.
* Correctly avoided inventing transaction-level causes.
* Correctly recognized that the evidence did not establish **why** individual
  categories increased.
* Approximate total duration: **87.4s**.
* Approximate `eval_count`: **1789**.

#### Qwen3 4B assessment

**Strengths**

* Strong tool selection.
* Strong structured tool-call behavior.
* Strong grounded interpretation.
* Good evidence discipline.
* Better reasoning quality than 1.7B in the tested scenarios.

**Weaknesses**

* Very high latency on tool selection and especially response generation.
* Unsupported temporal assumption when the year was ambiguous.
* Local hardware/resource constraints make interactive use potentially
  impractical.

**Classification**

* Quality: **promising**
* Latency: **concerning**
* Overall status: **evaluation baseline; not selected for initial MVP**

> Qwen3 4B is not permanently rejected. It remains available as a local
> evaluation baseline.
## 11.24 Initial Decision

Based on the initial feasibility experiments (see "Local LLM Experiment
Results" above), the **provisional** decision is:

> **Qwen3 1.7B is provisionally selected as the first local model for MVP
> integration through the provider-neutral `LLMClient`.** Ollama is the
> initial experimental inference runtime. This is a **provisional
> implementation choice, not a permanent model selection.**

### Rationale

* Qwen3 1.7B demonstrated **sufficient capability** for the tested agent
  behaviors: tool selection, multi-step planning, evidence-driven reasoning,
  and grounded response generation.
* **Substantially lower latency** on the available M2/8 GB hardware
  (approximately 4–12 seconds on several agent-oriented tests, versus
  approximately 30–87 seconds for Qwen3 4B).
* Tool calling works **when tool contracts are explicit**, which the runtime
  already enforces through `runtime/tools.py` and `validate_model_response()`.
* **Deterministic runtime safeguards** (tool validation, independent
  verification, authoritative analytical tools) compensate for known
  weaknesses such as sensitivity to prompt clarity and occasional
  argument-ordering errors.
* The provider-neutral `LLMClient` boundary **preserves the ability to
  replace the model later** without redesigning the agent.

### Important qualifications

* This is a **provisional** choice. It can be revisited after integration-level
  evaluation (section 14).
* Qwen3 1.7B demonstrated **sensitivity to tool-contract clarity** and produced
  incorrect tool-argument ordering under weaker instructions. Therefore
  runtime-side validation, deterministic tools, and independent verification
  remain **mandatory**, not optional.
* **Qwen3 4B remains installed as a local evaluation baseline** and may be
  reconsidered if Qwen3 1.7B proves insufficient during integration and full
  evaluation. It is not deleted.
* Neither Ollama nor Qwen3 1.7B is a permanent architectural commitment. The
  `LLMClient` boundary is.

## 11.25 Implementation Status and Next Steps

The first concrete provider adapter has been implemented: `OllamaLLMClient`
(`src/personal_finance_agent/llm/ollama.py`) adapts the provider-neutral
`LLMClient` to Ollama's local HTTP API using stdlib only (no SDK dependency).
This is documented in `docs/06_implementation.md` (Slice 6) and
`docs/09_decisions_and_changes.md` (DEC-022).

### Completed

* Provider-neutral `LLMClient` abstraction (`llm/` package).
* Feasibility experiments comparing Qwen3 4B and Qwen3 1.7B.
* Provisional model selection: Qwen3 1.7B (DEC-021).
* First concrete adapter: `OllamaLLMClient` (DEC-022).

### Remaining

1. Install Ollama locally (if not already present).
2. Verify the local runtime works.
3. Download the selected Qwen3 1.7B model.
4. Run a basic local inference test (e.g. a simple prompt).
5. Verify structured output / tool-calling capabilities.
6. Connect the adapter to the existing agent runtime.
7. Run the first spending-change explanation trajectory.
8. Evaluate the trajectory and response against the criteria in §11.14–§11.16.
9. Record results, including model/runtime versions and hardware context (§11.22).
10. Decide whether to retain Qwen3 1.7B or test alternatives.

These steps will be executed in a future implementation phase.

---

### Qwen3 1.7B results

#### Experiment 1 — grounded response (weaker instructions)

Given verified totals and category spending:

* Correctly identified **Shopping** as the dominant contributor.
* Correctly recognized **Food**, **Transport**, and **Entertainment** also
  increased.
* Correctly recognized **Bills** and **Other** as unchanged.
* **The initial response incorrectly stated that Transport stayed the same**,
  despite the underlying reasoning correctly calculating `+INR 500`.
* Approximate total duration: **22.1s**.
* Approximate `eval_count`: **930**.

#### Experiment 2 — tool calling (explicit dates, no strengthened semantics)

User asked about August 2026 vs September 2026, without explicit parameter
ordering guidance:

* Correct tool selected.
* **Incorrect argument ordering:** `period1 = 2026-09`, `period2 = 2026-08`,
  which violated the tool contract.
* Approximate total duration: **7.42s**.
* Approximate `eval_count`: **370**.

#### Experiment 3 — tool calling with explicit semantics and example

With explicit instructions that `period1` MUST be earlier, `period2` MUST be
later, and an example (`August 2026 -> September 2026`):

* Correct tool selected.
* Correct arguments: `period1 = 2026-08`, `period2 = 2026-09`.
* Approximate total duration: **4.42s**.
* Approximate `eval_count`: **187**.

#### Experiment 4 — multi-step analysis planning

Given verified total comparison plus `category_spending` and
`compare_period_spending` tools:

* Correctly recognized that category-level evidence was needed.
* Correctly avoided simply repeating the already-verified total comparison.
* Selected `category_spending` and requested September 2026 category analysis.
* Approximate total duration: **8.43s**.
* Approximate `eval_count`: **366**.

#### Experiment 5 — grounded response with stronger instructions

Given verified totals and verified category spending with strengthened
response instructions:

* Correctly identified **Shopping** as the dominant contributor.
* Correctly recognized other category increases.
* Correctly recognized **Bills** and **Other** as unchanged.
* Final response was concise and generally grounded.
* **The hidden reasoning still contained unsupported possibilities** (e.g. a
  sale, new purchase, or change in spending habits), but these were **not
  presented as established facts** in the final response.
* Approximate total duration: **11.97s**.
* Approximate `eval_count`: **569**.

#### Qwen3 1.7B assessment

**Strengths**

* Much lower latency than Qwen3 4B.
* Correct tool calling when tool semantics are explicit.
* Capable of basic evidence-driven planning.
* Capable of grounded response generation.
* Better suited to constrained local hardware.

**Weaknesses**

* More sensitive to prompt/tool-contract quality.
* Demonstrated incorrect tool-argument ordering under weaker instructions.
* Demonstrated a factual contradiction in an earlier final response
  (Experiment 1).
* Planning may be less complete than 4B.
* Requires strong runtime validation and deterministic analytical authority.

**Classification**

* Quality: **promising with guardrails**
* Latency: **substantially better**
* Overall status: **provisional initial MVP candidate**

---

### Comparative findings

> These experiments are preliminary and were conducted on a small set of
> manually constructed cases. They are **not** a statistically rigorous
> benchmark.

| Model | Tool calling | Grounded response | Observed latency | Main weakness | Current status |
|---|---|---|---|---|---|
| Qwen3 4B | Strong, including under ambiguity in tool call structure | Strong; avoided unsupported claims | ~30–87s per step | Very high latency; invented year under temporal ambiguity | Evaluation baseline; not selected for initial MVP |
| Qwen3 1.7B | Correct when semantics are explicit; failed ordering under weaker instructions | Generally grounded; one factual contradiction observed under weaker instructions | ~4–22s per step | Sensitive to contract clarity; weaker planning than 4B | Provisional initial MVP candidate |

---

### Architectural interpretation

The experiments **reinforce the existing architecture** in which:

* The **LLM proposes actions and generates grounded language**; it does not
  compute financial facts.
* **Deterministic tools remain authoritative** for arithmetic and analytical
  computation (`analytics.py`).
* The **runtime validates tool names and arguments** before execution
  (`runtime/tools.py`, `runtime/agent.py`).
* **Verification is independent of the model** (`runtime/checks.py`,
  `verification.py`).
* A failed verification **cannot be overridden by the model**.
* **Evidence, not model confidence, determines established financial facts**.

Specific observations that support this:

* **Temporal ambiguity (4B, Experiment 2):** the model invented `2023` when no
  year was given. A deterministic runtime must not trust such unsupported
  assumptions; explicit period handling and validation are required.
* **Tool-argument ordering (1.7B, Experiment 2):** the model reversed
  `period1`/`period2` under weaker instructions. Runtime argument validation
  must catch contract violations even when the model is otherwise capable.
* **Hidden-reasoning mismatch (1.7B, Experiment 5):** the model's internal
  reasoning contained unsupported possibilities while the final response was
  more conservative. This confirms that **the application must not depend on
  hidden reasoning traces**. The final structured output and verified evidence
  are what matter.
* **Factual contradiction (1.7B, Experiment 1):** the underlying reasoning was
  correct (`+INR 500`) but the final prose was wrong ("stayed the same"). This
  further confirms that **grounded responses must be traceable to verified
  observations**, not to model prose alone.

The observed sensitivity of 1.7B to **tool-contract clarity and explicit
instructions** confirms that **strong tool definitions and explicit prompts
materially affect small-model reliability**, which is exactly what the
deterministic runtime and verification layers are designed to mitigate.
