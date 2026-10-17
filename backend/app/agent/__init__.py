"""The reply agent, organized as five composable blocks.

Every LLM agent in this codebase is decomposed into the same five blocks so the
moving parts stay small and independently testable:

- ``config``         — :class:`AgentConfig`: models, sampling, retrieval knobs.
- ``system_prompt``  — the agent's standing instructions to the model.
- ``state``          — :class:`AgentState`: everything pulled from memory
                       (persona, rules, RAG-retrieved emails & past edits).
- ``input``          — turns ``state`` + the incoming email into the user prompt.
- ``output``         — parses the raw model text into a structured result.

``agent.ReplyAgent`` is the orchestrator that wires the five blocks together.
It reaches Gmail exclusively through ``app.mcp`` (the MCP client), memory
exclusively through ``app.rag``, and the model through ``app.core.llm``.

Submodules are not imported eagerly; import the block you need directly, e.g.
``from app.agent.agent import ReplyAgent``.
"""

__all__ = []
