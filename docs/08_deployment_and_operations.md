# 1. Deployment and Operations Overview

This document defines how the Personal Finance Agent should be run, deployed, monitored, maintained, and evolved operationally. It follows the problem and objectives in `docs/01_problem_and_objectives.md`, requirements in `docs/02_requirements.md`, system design in `docs/03_system_design.md`, agent design in `docs/04_agent_design.md`, data design in `docs/05_data_design.md`, implementation plan in `docs/06_implementation.md`, and testing/evaluation plan in `docs/07_testing_and_evaluation.md`.

**Development** is the activity of changing and inspecting the software. **Deployment** is making a selected version available in an execution environment. **Operations** covers running it, observing behavior, handling failures, protecting data, releasing changes, and maintaining the system over time.

Operational concerns matter even for an agentic prototype because transaction data is sensitive, agent behavior can fail in non-obvious ways, and a useful result depends on the interaction between data loading, analysis, verification, and response generation. The project should nevertheless avoid production infrastructure that current requirements do not justify.

The operating principle is:

**Operational complexity should be proportional to actual system requirements.**

For the MVP, local reproducibility, safe configuration, basic logging, testing, evaluation, and version-based recovery are sufficient. Hosted services, persistent production data, container orchestration, and high-availability mechanisms remain future options.

# 2. Operational Goals

## 2.1 Reproducibility

A developer should be able to recreate the local environment, run controlled sample data, and reproduce important analytical and evaluation results. Versioned code, documented configuration, and deterministic fixtures support this goal.

## 2.2 Reliability

Supported inputs should behave predictably, and failures should be visible rather than silently converted into fabricated insights. Deterministic analytics and verification should have stable operational behavior.

## 2.3 Observability

An execution should eventually be inspectable through request, action, result, verification, error, timing, and response information. The initial approach should remain simple and privacy-aware.

## 2.4 Maintainability

Operations should make it straightforward to update code, data handling, instructions, analytical capabilities, tests, and documentation without hidden environment dependencies.

## 2.5 Controlled configuration

Runtime choices should be explicit and separated from source code. Environment-specific settings and secrets must not be mixed into the application logic.

## 2.6 Predictable failures

Invalid data, unavailable capabilities, model failures, verification failures, and unexpected exceptions should result in bounded, diagnosable outcomes.

## 2.7 Security and privacy

Transaction data, credentials, logs, configuration, and evaluation artifacts should receive handling appropriate to their sensitivity. The MVP should minimize persistence and unnecessary exposure.

## 2.8 Cost awareness

Where model or external computation is introduced, usage should be observable before optimization or budget decisions are made. Deterministic local computation should remain the default where appropriate.

## 2.9 Recoverability

The MVP should be recoverable through source control, reproducible local data, and rerunnable tests/evaluations. More advanced backup and disaster recovery are future concerns tied to persistence.

## 2.10 Ease of development and deployment

The local workflow should remain simple enough for a solo learning and portfolio project. Deployment should not require infrastructure work unrelated to demonstrating the approved system behavior.

## 2.11 Extensibility

Operational boundaries should leave room for later hosted execution, persistent storage, richer interfaces, and multiple users without making those systems part of the MVP.

# 3. Environment Strategy

## 3.1 Development

Development is the local environment where code, data handling, analytical tools, agent behavior, and documentation are changed. The current project uses a macOS workstation with Python and `uv`.

## 3.2 Test

Test is the process or local execution context used to run automated unit, integration, analytical, verification, agent, and regression tests. It does not require a separate server or infrastructure for the MVP.

## 3.3 Staging

Staging is an optional future environment used to validate deployment behavior, configuration, security, and operational changes before production. It is not required while the project remains a local prototype.

## 3.4 Production

Production is a future environment for a hosted or user-facing service with stronger requirements for access control, persistence, availability, monitoring, backups, incident handling, and release management. No production environment is assumed or selected now.

The environments are conceptual stages, not necessarily separate machines or deployments. For the MVP, development and test may both be local executions using controlled data.

# 4. Local Development Environment

The current local development environment includes:

- **macOS:** The current development operating system.
- **Apple Silicon:** Relevant to local interpreter and dependency compatibility if a dependency is later introduced.
- **Python 3.12+:** The implementation runtime established in `pyproject.toml` and `06_implementation.md`.
- **`uv`:** The existing Python environment and dependency-management workflow.
- **Git:** Version control for source, documentation, configuration templates, and known-good versions.
- **VS Code:** The current development editor and project workspace.

Local reproducibility should depend on the declared Python requirement, `pyproject.toml`, safe sample data, documented setup, and version-controlled source rather than undocumented machine state. No additional machine-specific assumptions should be introduced without a concrete compatibility reason.

# 5. Application Runtime

The application should conceptually run as a local, self-contained process for the MVP.

The runtime flow is:

```text
Application Entry Point
  -> Load Non-sensitive Configuration
  -> Load Transaction Data
  -> Validate and Normalize Data
  -> Create Agent Execution State
  -> Understand Request and Select Actions
  -> Run Analytical Capabilities
  -> Observe and Validate Results
  -> Verify Important Results
  -> Generate Grounded Response
  -> Emit Logs and Return Result
```

The entry point is currently represented by `main.py` during the repository's incremental implementation. The final runtime command and user interface are TBD; this document does not invent a command that has not been established in `06_implementation.md`.

The runtime should keep deterministic analytics, agent state, verification, response generation, and logging as logical boundaries within the same application. It should return bounded errors for invalid data, unavailable actions, reasoning failures, and verification failures.

# 6. Configuration Management

## 6.1 Non-sensitive configuration

Non-sensitive configuration may include:

- Input or sample-data path.
- Supported feature flags.
- Logging level.
- Runtime options.
- Model settings if a model is selected.
- Analytical parameters and thresholds once justified.
- Evaluation-case selection.

Configuration should not be hard-coded unnecessarily and should be separated from domain logic. Defaults should be suitable for local development.

## 6.2 Sensitive configuration

Sensitive configuration may include:

- API keys.
- Credentials.
- Access tokens.
- Private service connection values.

Secrets must not be committed to Git, embedded in source code, placed in sample data, or written to logs. A local environment-variable approach may be sufficient for the MVP. No secret-management platform is selected.

Environment-specific configuration should be separated from source code. If configuration changes affect analytical scope, model behavior, or evaluation results, the effective configuration should be identifiable in the execution record without exposing secrets.

# 7. Data Deployment and Lifecycle

The operational data flow is:

```text
Load Source Data
  -> Validate
  -> Normalize
  -> Categorize / Enrich if supported
  -> Use in Analysis
  -> Produce Derived Results
  -> Provide Relevant Agent Context
  -> Retain Verification Evidence for the Task
  -> Delete or Release Temporary Data
```

For the MVP:

- Transaction data may be loaded locally for an execution or controlled test.
- Invalid records should receive explicit validation outcomes.
- Canonical transactions and derived results may remain in memory for the active task.
- Temporary files should be removed or excluded from version control when no longer needed.
- Long-term persistence is not assumed.
- Private real transaction data should not be committed to the repository.

If persistent storage is introduced later, the project must define retention, deletion, access, backup, restoration, migration, and privacy policies before relying on it operationally. Derived data should not be retained merely because it can be generated.

# 8. Deployment Model

## 8.1 MVP deployment

The MVP should use a simple local or self-contained execution model. This is sufficient for a learning and portfolio project whose primary goals are to validate data processing, deterministic analysis, agent behavior, verification, and evaluation.

A local model avoids premature hosting, authentication, network, persistence, scaling, and operational complexity. It also makes controlled synthetic data and reproducible evaluation easier to manage.

## 8.2 Future deployment

If the system evolves into a hosted application, a conceptual progression may be:

```text
Local
  -> Development Environment
  -> Staging
  -> Production
```

The exact hosting model, provider, networking, persistence, access control, and release automation are TBD. They should be selected only after the implementation and evaluation results establish actual operational requirements.

# 9. Containerization Considerations

Containerization may provide:

- Reproducible runtime environments.
- Dependency isolation.
- Deployment consistency.
- A simpler path to some future hosting environments.

It also adds:

- Build and maintenance overhead.
- Another configuration surface.
- More debugging complexity for a small local application.
- Potentially unnecessary operational work before the runtime requirements are understood.

Containerization is **not required for the MVP**. It is an optional future capability and remains TBD. No container configuration should be created merely to make the repository appear production-ready.

# 10. Production Deployment Considerations

If the project becomes a real hosted service, future operational design may need to address:

- Application hosting and runtime isolation.
- Persistent transaction storage and lifecycle policies.
- Authentication and authorization.
- Secure handling of transaction data.
- Secure transport and network boundaries.
- Monitoring, alerting, and operational dashboards.
- Backups and restoration.
- Scaling for larger workloads or multiple users.
- Deployment automation and release approval.
- Incident response and security operations.
- Rollback and data-migration procedures.

These are future considerations, not an initial production architecture. No cloud provider, database, load balancer, orchestration platform, or service topology is selected.

# 11. Observability

The system should eventually expose enough information to understand an agent execution and its operational outcome.

Conceptual events include:

- Request received.
- Request interpretation.
- Agent plan created or updated.
- Action selected.
- Tool/action execution started and completed.
- Analytical result produced.
- Validation outcome.
- Verification requested and completed.
- Replanning or recovery.
- Error or unsupported request.
- Response generation.
- Final response returned.
- Execution duration.
- Model usage or cost where applicable.

## 11.1 Logs

Logs contain detailed execution and diagnostic information, such as statuses, errors, action names, timing, and safe evidence references. Logs must avoid unnecessary raw transaction data, credentials, tokens, and sensitive user information.

## 11.2 Metrics

Metrics are aggregated measurements such as request count, success/failure count, action count, execution duration, verification failures, evaluation results, and model usage where available. The initial implementation can record simple local measurements.

## 11.3 Traces and trajectories

A trajectory records the sequence of agent interpretation, planning, actions, observations, state updates, verification, replanning, and response. Trajectories are important for evaluation even if the MVP stores them only locally or in test artifacts.

No specific observability platform or distributed tracing system is selected.

# 12. Monitoring

Monitoring should evolve with system complexity.

## 12.1 System health

Eventually monitor application availability, unhandled failures, execution duration, memory/CPU usage where relevant, and process termination. The MVP can rely on local execution output and test results.

## 12.2 Agent health

Monitor agent execution failures, action/tool failures, verification failures, repeated replanning, unexpected action sequences, and safe inability-to-answer outcomes.

## 12.3 Data health

Monitor invalid records, missing required fields, unexpected currencies, duplicate indicators, processing failures, and changes in source format or distributions.

## 12.4 Quality health

Monitor regression failures, numerical correctness, groundedness issues, fabrication findings, ambiguity failures, and evaluation performance. Quality monitoring is especially important because an application can remain available while producing worse insights.

## 12.5 Cost health

If model or external services are introduced, monitor calls, usage, token counts where available, and cost-related measurements. No provider or budget is selected.

# 13. Alerting

Operational attention may eventually be triggered by:

- Repeated application failures.
- Repeated analytical or tool failures.
- Verification failures above an expected level.
- Data-processing failures or unexpected source changes.
- Unexpected model or external-service usage/cost.
- Evaluation regression.
- Security or privacy incidents.
- Repeated inability to produce grounded responses.

The MVP does not require an alerting platform. Exact alert conditions and thresholds should be defined only after actual operating characteristics and deployment requirements are known.

# 14. Reliability

Reliability principles for the system are:

- Deterministic analytical components should fail predictably and report status.
- Agent failures must not silently produce fabricated results.
- Verification failures should prevent unsupported conclusions where appropriate.
- Errors and important state transitions should be observable.
- Partial failures should produce qualified results, clarification, or safe termination.
- Source, canonical, analytical, and verification state should not become silently inconsistent.
- A successful process exit should not be treated as evidence that the analytical result is correct.

No distributed fault-tolerance mechanism is required for the local MVP.

# 15. Recovery and Resilience

Recovery should remain simple and proportional to the current runtime.

Potential recovery behavior includes:

- Retrying a transient model or service failure when a later provider is introduced.
- Restarting an interrupted local execution from the original request and data.
- Replanning after an invalid analytical action.
- Handling unavailable capabilities with a safe limitation or alternative analysis.
- Rejecting or isolating malformed data.
- Re-running deterministic verification.
- Terminating safely when recovery cannot produce a grounded result.

The MVP should avoid complex distributed recovery, queues, failover systems, and state replication. The active in-memory execution can be restarted rather than recovered from persistent workflow state.

# 16. Cost Management

Potential costs include:

- Model or API calls.
- Token usage.
- Local or hosted compute.
- Storage.
- External services.

For the MVP:

- Measure usage before optimizing aggressively.
- Avoid unnecessary model calls if a deterministic operation is sufficient.
- Prefer local deterministic computation for arithmetic and aggregation.
- Avoid infrastructure that creates recurring cost without a current requirement.
- Record enough configuration and usage information to compare evaluation runs where applicable.

No monthly budget or cost threshold is invented here.

# 17. Security Operations

Operational security principles include:

- Keep secrets outside source control and outside logs.
- Limit access to transaction data and derived evidence.
- Use secure local configuration practices.
- Avoid unnecessary raw financial information in logs and evaluation artifacts.
- Review dependencies and update them when justified.
- Treat user-provided files and text as untrusted input.
- Protect model/service credentials if external interactions are introduced.
- Validate data before using it in analysis.
- Keep operational artifacts separate from private transaction data.

No compliance framework, authentication system, encryption technology, or hosted security architecture is selected for the MVP.

# 18. Privacy Operations

## 18.1 MVP considerations

The MVP should minimize data collection and persistence, use controlled synthetic data for development and evaluation where possible, avoid committing private records, and keep sensitive values out of logs and trajectories unless needed for a specific test.

Temporary transaction data should be deleted or released when the task or test no longer needs it. Derived insights should not be treated as harmless automatically; aggregate spending information can also reveal personal behavior.

## 18.2 Future hosted-system considerations

A hosted or multi-user system would require explicit policies for data isolation, retention, deletion, access, external model/API transmission, audit information, and user control. Data sent to an external model or service would require a deliberate privacy decision and should be minimized.

The MVP does not establish a full privacy program or legal/compliance framework.

# 19. Backup and Recovery

For the MVP, persistent backup infrastructure may not be necessary when transaction data is locally supplied, synthetic, reproducible, or intentionally temporary. Source code and documentation are recoverable through Git, and sample data should be safely reproducible.

If persistent data is introduced later, operations must define:

- Backup frequency.
- Retention duration.
- Backup protection.
- Restoration procedures.
- Data consistency checks.
- Migration handling.
- Recovery objectives appropriate to actual use.
- Disaster-recovery scope.

No backup service, schedule, or disaster-recovery infrastructure is selected now.

# 20. Release Strategy

The conceptual release path is:

```text
Development
  -> Automated Tests
  -> Evaluation
  -> Review
  -> Release
```

Every release should ideally pass:

- Relevant automated tests.
- Deterministic analytical and verification tests.
- Relevant evaluation cases.
- Regression checks.
- Documentation review for changed behavior or decisions.

For future hosted deployment, a staging environment should be considered before production. The MVP can use a local known-good version and documented test/evaluation results as its release evidence.

# 21. Rollback Strategy

For the MVP, Git should provide a straightforward way to return to a known-good source and documentation version. A problematic change should be identified, isolated, and reverted or corrected after the relevant tests and evaluation cases are rerun.

Future deployment may require rollback of:

- The previous application version.
- Configuration changes.
- Prompt or model configuration.
- Data migrations.
- Persistent analytical or state changes.

Rollback procedures must account for compatibility between application versions and stored data if persistence is introduced. No automated rollback infrastructure is designed now.

# 22. Incident Handling

Potential incidents include:

- Application unavailable or unexpectedly terminating.
- Incorrect financial analysis discovered.
- Verification failure or groundedness regression.
- Data corruption or malformed input causing unsafe behavior.
- Model or external-service failure.
- Security incident.
- Privacy incident.
- Evaluation regression after a change.

The conceptual process is:

```text
Detect
  -> Investigate
  -> Contain
  -> Recover
  -> Validate
  -> Document
  -> Prevent recurrence
```

For the MVP, this may be a focused engineering investigation: preserve the failing case and trajectory, identify the affected component, correct or revert the change, rerun relevant tests/evaluation, and document the outcome. Formal enterprise incident-management processes are not required.

# 23. Maintenance

Ongoing maintenance should cover:

- Python and runtime dependency updates.
- Model or provider updates if introduced.
- Prompt and instruction updates.
- Analytical logic changes.
- Test and regression-suite maintenance.
- Evaluation dataset maintenance.
- Documentation and decision-log updates.
- Security and secret-handling updates.
- Data-schema and input-format evolution.
- Observability and privacy review.

Changes to agent behavior, prompts, models, tools, verification, or data processing should trigger relevant regression evaluation. A change should not be treated as an improvement solely because one example looks better.

# 24. Model and Agent Operations

If a model-based reasoning component is introduced, operations should track:

- Model version changes.
- Prompt or instruction changes.
- Tool and tool-contract changes.
- State and context changes.
- Evaluation results before and after the change.
- Cost and latency changes.
- Fabrication, groundedness, safety, and recovery regressions.

A model or prompt update is a change to system behavior, not merely a dependency update. It should be evaluated against preserved cases and relevant trajectories before becoming the new known-good version.

# 25. Data and Model Drift

## 25.1 Data drift

Transaction formats, merchant descriptions, categories, currencies, source fields, and data distributions may change. Signs include increased validation failures, new description patterns, unexpected direction values, changed category coverage, or altered transaction volume.

The initial response should be targeted validation and evaluation rather than complex drift infrastructure. A source-format change should be captured as a reproducible data case and handled through the data pipeline.

## 25.2 Model or behavior changes

Changing a model, provider, prompt, or reasoning configuration may alter intent interpretation, action selection, response style, fabrication risk, latency, and cost. Regression evaluation and trajectory comparison should be used to detect these changes.

No specialized machine-learning drift-monitoring system is required or selected.

# 26. Operational Metrics

Candidate operational metrics include:

## 26.1 Reliability

- Success rate.
- Failure rate.
- Verification failure rate.
- Safe inability-to-answer rate.

## 26.2 Performance

- Response latency.
- Total execution duration.
- Number of analytical actions.
- Time spent in data loading, analysis, verification, and response generation.

## 26.3 Agent behavior

- Average actions per task.
- Unnecessary actions.
- Replanning frequency.
- Clarification frequency.
- Action failure and recovery frequency.

## 26.4 Cost

- Model calls.
- Token usage where available.
- External-service usage.
- Cost per request where measurable.

## 26.5 Quality

- Evaluation score.
- Numerical accuracy.
- Groundedness.
- Fabrication rate.
- Regression failures.

These are candidate measurements only. No operational threshold, service-level objective, or cost target is defined yet.

# 27. Development-to-Production Lifecycle

The complete operational lifecycle is:

```text
Design
  -> Implement
  -> Test
  -> Evaluate
  -> Release
  -> Deploy
  -> Monitor
  -> Analyze
  -> Improve
  -> Re-evaluate
```

For the MVP, the lifecycle ends primarily in local execution, evaluation, and iterative improvement. If a hosted system is later justified, deployment and operations become additional stages rather than reasons to add infrastructure before the system is reliable.

This closes the feedback loop established by the project documents: requirements guide implementation, testing and evaluation expose gaps, and operations provide evidence about runtime behavior and maintenance needs.

# 28. MVP Operations Plan

The MVP should require only:

- A local reproducible Python environment.
- Version-controlled source, documentation, and safe sample data.
- Controlled non-sensitive configuration.
- Safe local secret handling if external model access is introduced.
- Basic logging and execution identifiers.
- Automated test execution.
- Evaluation execution and preserved case results.
- Basic error reporting.
- Git-based rollback to a known-good version.

The MVP should not require by default:

- Kubernetes or cloud orchestration.
- Distributed monitoring.
- Complex CI/CD.
- A production database.
- Load balancing.
- High-availability infrastructure.
- Message queues or microservices.
- A dedicated alerting platform.
- Containerization.

Infrastructure should be added only when the actual implementation requires it or a later deployment requirement justifies it.

# 29. Future Operations Evolution

Operations can evolve through stages:

## Stage 1 - Local prototype

Simple local execution, controlled data, basic logging, tests, evaluation, and Git-based recovery.

## Stage 2 - Reproducible development environment

Consistent dependencies, configuration templates, repeatable test/evaluation execution, and clearer local setup.

## Stage 3 - Hosted prototype

A selected deployment environment, basic access controls, deployment configuration, operational monitoring, and controlled data handling.

## Stage 4 - Production-oriented system

Persistent data, stronger security and privacy controls, backups, incident handling, release management, monitoring, and recovery procedures.

## Stage 5 - Larger system

Scaling, richer infrastructure, multiple users, more complex workflows, and potentially additional specialized components if requirements justify them.

These stages are future options, not implementation commitments for the current project.

# 30. Deployment and Operations Decisions

| Decision | Rationale | Status |
|---|---|---|
| Run the MVP locally | The project is primarily a learning and portfolio project, and local execution is sufficient to demonstrate the approved workflow. | Decided |
| Do not require production infrastructure now | Hosting, scaling, persistence, and high availability are not current MVP requirements. | Decided |
| Do not require Docker initially | Containerization adds complexity without a current deployment requirement. | Decided |
| Begin observability with simple local logging | The MVP needs inspectable execution behavior but not a distributed monitoring platform. | Decided |
| Use Git-based version rollback for the MVP | Known-good source and documentation versions can be restored without deployment infrastructure. | Decided |
| Include evaluation in the release process | A working demo is insufficient; changes must be checked against tests and evaluation cases. | Decided |
| Separate secrets from source code | Financial and model-service credentials must not be committed or exposed. | Decided |
| Defer persistent storage | Current requirements support local/temporary data handling and do not require long-term persistence. | Decided for MVP; future need TBD |
| Select a hosting provider | No hosted deployment requirement or operational evidence exists yet. | TBD |
| Select monitoring and alerting platforms | Platform choice depends on future deployment scale and observed operational needs. | TBD |
| Define production recovery objectives | No production workload or availability requirement has been established. | TBD |
| Define long-term data retention and backup policy | Persistence and user-data lifecycle remain unresolved. | TBD |

# 31. Open Questions / TBD

The following operational questions remain unresolved:

- What deployment target, if any, will follow the local prototype?
- Which hosting provider or execution environment would be appropriate for a hosted version?
- Is containerization justified by a later deployment requirement?
- Is persistent storage required, and what data should it retain?
- What authentication and authorization model is needed for multiple users?
- Is CI/CD required once deployment becomes repeatable?
- Which monitoring and alerting platform, if any, is justified?
- What backup and disaster-recovery strategy is appropriate for persistent data?
- What scaling requirements should be supported?
- What production service-level objectives, if any, should be defined?
- What cost budgets or usage limits are appropriate after actual usage is measured?
- What data retention and deletion policies are required?
- What security implementation is needed for hosted execution?
- How should model/provider operations, version changes, and external-service failures be managed?
- What privacy controls are needed for data sent to external model or API providers?
- What release and rollback automation is justified?

These questions remain TBD and should be resolved from actual implementation, evaluation, and operational requirements rather than infrastructure assumptions.

# 32. Handoff to Decision Log

This document establishes the local-first operational model, environment distinctions, runtime expectations, configuration and secret handling, data lifecycle, deployment boundaries, observability, monitoring, alerting, reliability, recovery, cost awareness, security and privacy operations, release and rollback practices, incident handling, maintenance, model operations, drift considerations, operational metrics, and future evolution path.

Major decisions made throughout the project should be recorded in `docs/09_decisions_and_changes.md`. The decision log should track:

- Date.
- Decision.
- Context.
- Alternatives considered.
- Rationale.
- Consequences.
- Status.
- Subsequent changes.

The decision log should remain a living record throughout implementation and future iterations so operational changes can be understood in relation to the requirements, design, tests, and evaluation evidence.
