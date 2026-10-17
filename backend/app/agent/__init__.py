"""The reply agent, organized as six composable blocks.

Every LLM agent in this codebase is decomposed into the same six blocks so the
moving parts stay small and independently testable:

- ``config``         — :class:`AgentConfig`: models, sampling, retrieval knobs.
- ``system_prompt``  — the agent's standing instructions to the model.
- ``state``          — :class:`AgentState`: everything pulled from memory
                       (persona, rules, RAG-retrieved emails & past edits).
- ``input``          — turns ``state`` + the incoming email into the user prompt.
- ``output``         — parses the raw model text into a structured result.
- ``tools``          — :class:`AgentTools`: what the agent can *do* besides
                       calling the model (Gmail over MCP, memory writes via RAG).

``agent.ReplyAgent`` is the orchestrator that wires the five blocks together.
Side effects go through ``tools`` (which is backed by ``app.mcp`` and
``app.rag``); reads of memory go through ``state`` (backed by ``app.rag``); the
model is reached through ``app.core.llm``.

Submodules are not imported eagerly; import the block you need directly, e.g.
``from app.agent.agent import ReplyAgent``.
"""

__all__ = []
