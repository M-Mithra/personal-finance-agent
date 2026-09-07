"""Agent runtime lifecycle.

This package implements the deterministic agent runtime described in
``docs/04_agent_design.md`` (sections 3, 6-12, 14-16): an explicit lifecycle of
understanding, planning, action selection, execution, observation, validation,
verification, state update, replanning, and grounded response generation.

The runtime is deliberately deterministic. Request understanding, planning,
replanning, and response generation are rule-based so the lifecycle and its
interfaces can be tested now and later have selected decisions replaced by
LLM-based reasoning without redesigning the system.

Module responsibilities:

- ``state``    : typed lifecycle vocabulary and the explicit agent state.
- ``understanding``: deterministic recognition of supported intents and periods.
- ``planning`` : deterministic planner producing structured actions.
- ``tools``    : the action/tool interface to the analytical capabilities.
- ``checks``   : wiring between tool results and the verification layer.
- ``replanning``: bounded follow-up decisions made after observing results.
- ``response`` : deterministic grounded response generation.
- ``agent``    : the runtime loop wiring the stages together.

No LLM, agent framework, or external service is involved.
"""
