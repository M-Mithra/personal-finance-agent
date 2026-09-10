# Personal Finance Agent

A Python project for personal transaction and spending analysis, demonstrating a complete agent-engineering lifecycle from deterministic analytics through an experimental LLM-driven agent loop.

## What It Does

The Personal Finance Agent analyzes transaction/spending data to answer questions like:

- How much did I spend in a given period?
- How does spending compare across months?
- What categories or merchants contributed most to spending?
- Why did spending increase or decrease?

It distinguishes between **observed facts** (computed from transaction data), **evidence-supported interpretations**, and **unsupported assumptions**.

## Architecture

The project is built in slices, from deterministic foundation to experimental LLM integration:

### Deterministic Analytical Foundation
- Canonical transaction model with exact `Decimal` arithmetic
- Spending summary, category analysis, merchant analysis, noteworthy transactions, period comparison
- CSV loading with validation and normalization
- Committed synthetic sample data for reproducible tests

### Deterministic Verification
- Independent recomputation of analytical results
- Trust classification: verified / failed / inconclusive / unverified
- Verification is separate from analysis and cannot be overridden

### Deterministic Agent Runtime
- Explicit lifecycle: Understand → Plan → Act → Observe → Validate → Update State → Replan → Verify → Respond
- Explicit `AgentState` with full trajectory recording
- Deterministic understanding (keyword matching), planning, and response generation

### Experimental LLM-Driven Execution Loop (DEC-023)
- Opt-in bounded loop that uses an LLM as a reasoning subroutine
- LLM proposes tool calls or final responses; runtime validates, executes, verifies
- Budgets: 6 model steps / 4 tool calls / 2 repeated identical calls / 1 invalid-response retry
- Reversed `period_comparison` periods rejected (not normalized)
- Deterministic grounding gate on currency-anchored monetary figures
- Hybrid pending-action handling: deterministic gap-fill after LLM tool calls

### Provider-Neutral LLM Abstraction
- `LLMClient` interface: `model_identifier`, `complete`, `reason`, `generate_response`
- Structured response types (`ToolCall`, `ModelResponse`, `LLMRequest`)
- Tool definitions, error vocabulary, deterministic `FakeLLMClient` for tests
- No provider SDK or hard-coded model dependencies in the runtime

### Local LLM Integration (Experimental)
- `OllamaLLMClient` adapter for Ollama's local HTTP API (stdlib only, no SDK)
- Qwen3:1.7B is the current **provisional** MVP model candidate
- Qwen3:4B retained as evaluation baseline
- Live experiments require Ollama running locally

## Current Status

| Component | Status |
|---|---|
| Deterministic analytics | Implemented and tested |
| Deterministic verification | Implemented and tested |
| Deterministic agent runtime | Implemented and tested |
| Provider-neutral LLM abstraction | Implemented and tested |
| Ollama adapter | Implemented and tested |
| LLM-driven execution loop (DEC-023) | Implemented and tested |
| DEC-023 decision status | **PROPOSED / provisional-experimental** |
| Qwen3:1.7B via Ollama | Provisional MVP candidate |
| Full evaluation | **Not yet completed** |

**This is not a production-ready system.** The LLM integration is experimental and provisional. The deterministic path remains the default and regression baseline.

## Testing

Run the full test suite:

```bash
uv run python -m unittest discover -s tests
```

Current test suite: **210 tests, all passing** (including 35 LLM-loop tests with `FakeLLMClient`).

The LLM-loop tests are fully deterministic and require no Ollama instance. Live Ollama tests live under `tests/integration/` and are skipped unless Ollama is reachable.

## Local LLM Experiments

To run live experiments with a local model:

1. Install and run [Ollama](https://ollama.ai/)
2. Pull the model: `ollama pull qwen3:1.7b`
3. Ensure Ollama is running on `http://localhost:11434`

The LLM integration is experimental. Live model behavior is non-deterministic; budgets, verification, and deterministic fallback exist precisely because of this.

## Documentation

Detailed documentation is in the `docs/` directory:

- `docs/01_problem_and_objectives.md` — Problem statement and objectives
- `docs/02_requirements.md` — Functional, agent, data, safety, and non-functional requirements
- `docs/03_system_design.md` — High-level system architecture and boundaries
- `docs/04_agent_design.md` — Agent behavior, runtime model, state, planning, evaluation considerations
- `docs/05_data_design.md` — Logical transaction data model
- `docs/06_implementation.md` — Implementation slices, module mapping, development workflow
- `docs/07_testing_and_evaluation.md` — Testing strategy, evaluation phases, LLM-loop test evidence
- `docs/08_deployment_and_operations.md` — Deployment and operations approach
- `docs/09_decisions_and_changes.md` — Engineering decision log (including DEC-023)
- `docs/10_llm_integration_design.md` — LLM integration architecture and boundary design
- `docs/11_local_llm_integration.md` — Local LLM experiments, Qwen3 results, live verification

## Project Philosophy

- **Start simple** — Build a working vertical slice before adding complexity
- **Evidence before complexity** — Add infrastructure only when justified by requirements
- **Deterministic where possible** — Use conventional computation for arithmetic, filtering, aggregation
- **LLM/agent where useful** — Use reasoning for understanding, planning, interpretation
- **Verification is part of the system** — Important outputs are checked against data
- **Evaluation-driven development** — Agent quality is assessed through defined cases, not impressions
- **Documentation as an engineering artifact** — Decisions and reasoning are recorded as the system evolves

## License

This project is for learning and demonstration purposes.

