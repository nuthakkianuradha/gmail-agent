"""Agent block: **config**.

Static, per-run configuration for the reply agent — which models to call, how to
sample, and how much memory to retrieve. This is distinct from
:mod:`app.config` (process/environment settings): ``AgentConfig`` is the agent's
*behavioral* configuration and can be varied per request or per experiment
without touching env vars.

``AgentConfig.default()`` is the one place env leaks in: it picks
``primary_model`` for whichever LLM provider is active (``LLM_PROVIDER``), so a
local Ollama model name never gets sent to Groq or vice versa.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    # --- LLM ---
    primary_model: str = "openai/gpt-oss-120b"           # Groq default (cloud mode)
    fallback_model: str = "google/gemini-2.0-flash-001"  # OpenRouter (fallback)
    temperature: float = 0.7
    max_tokens: int = 1024

    # --- Memory / RAG retrieval (feeds the ``state`` block) ---
    match_count: int = 8
    match_threshold: float = 0.4
    memory_source_types: tuple[str, ...] = ("email", "modification")

    @classmethod
    def default(cls) -> "AgentConfig":
        """Default config for the active LLM provider."""
        from app.config import get_settings  # local import: keep the block leaf-like

        s = get_settings()
        if s.llm_provider == "local":
            return cls(primary_model=s.local_llm_model)
        return cls()


if __name__ == "__main__":
    cfg = AgentConfig.default()
    print("AgentConfig (default):")
    print(f"  primary_model:  {cfg.primary_model}")
    print(f"  fallback_model: {cfg.fallback_model}")
    print(f"  temperature:    {cfg.temperature}")
    print(f"  max_tokens:     {cfg.max_tokens}")
    print(f"  match_count:    {cfg.match_count}")
    print(f"  match_threshold:{cfg.match_threshold}")
    print(f"  memory_sources: {cfg.memory_source_types}")
    print("AgentConfig module OK")
