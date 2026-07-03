"""Agent block: **config**.

Static, per-run configuration for the reply agent — which models to call, how to
sample, and how much memory to retrieve. This is distinct from
:mod:`app.config` (process/environment settings): ``AgentConfig`` is the agent's
*behavioral* configuration and can be varied per request or per experiment
without touching env vars.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    # --- LLM ---
    primary_model: str = "llama-3.3-70b-versatile"      # Groq (fast, primary)
    fallback_model: str = "google/gemini-2.0-flash-001"  # OpenRouter (fallback)
    temperature: float = 0.7
    max_tokens: int = 1024

    # --- Memory / RAG retrieval (feeds the ``state`` block) ---
    match_count: int = 8
    match_threshold: float = 0.4
    memory_source_types: tuple[str, ...] = ("email", "modification")

    @classmethod
    def default(cls) -> "AgentConfig":
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
