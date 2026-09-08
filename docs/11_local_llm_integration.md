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

## 11.24 Initial Decision

The current decision is:

> We will initially investigate Ollama running Qwen3 4B locally as an experimental LLM backend for the Personal Finance Agent. This is not yet a permanent model or runtime commitment. The provider-neutral ``LLMClient`` remains the architectural boundary.

This decision:

* Does **not** permanently commit the project to Ollama as the inference runtime.
* Does **not** permanently commit the project to Qwen3 4B as the model.
* Does **not** abandon the provider-neutral ``LLMClient`` abstraction.
* Does **not** redesign the existing agent runtime or verification architecture.

## 11.25 Handoff to Implementation

After this design is approved, the next implementation phase should:

1. Install Ollama locally.
2. Verify the local runtime works (e.g. basic model call).
3. Download the selected Qwen3 4B model.
4. Run a basic local inference test (unstructured prompt).
5. Verify structured-output and/or tool-calling capabilities experimentally.
6. Implement the Ollama-backed ``LLMClient`` adapter.
7. Connect it to the existing agent runtime.
8. Run the first spending-change explanation trajectory (§11.10).
9. Evaluate the trajectory and response using the cases in §11.15.
10. Record latency, memory usage, and quality observations.
11. Decide whether to retain Qwen3 4B or test alternatives.

These steps will be executed in a future implementation phase.
