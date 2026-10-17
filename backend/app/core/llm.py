"""Chat completions through a provider chain.

The primary provider is chosen by ``LLM_PROVIDER`` (see :mod:`app.config`):

* ``local`` — Ollama (or any OpenAI-compatible local server) at
  ``LOCAL_LLM_BASE_URL``. No API key, no network, no per-token cost.
* ``groq``  — Groq cloud.

Whatever the primary, cloud providers whose keys are configured act as
fallbacks, in the order **local → Groq → OpenRouter**. All three speak the
OpenAI chat-completions API, so one client class covers them.

This module is deliberately generic: it knows nothing about email drafts or
diff summaries. Callers (the agent, the RAG learning loop) bring their own
prompts and call :func:`chat`.
"""

import logging

from openai import AsyncOpenAI

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# Cloud model names live here (and are mirrored by AgentConfig's defaults).
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
GROQ_SUMMARY_MODEL = "llama-3.1-8b-instant"
OPENROUTER_DEFAULT_MODEL = "google/gemini-2.0-flash-001"

# Ollama ignores the API key, but the SDK insists on a non-empty one.
local_client = AsyncOpenAI(api_key="ollama", base_url=settings.local_llm_base_url)
groq_client = AsyncOpenAI(
    api_key=settings.groq_api_key or "unset",
    base_url="https://api.groq.com/openai/v1",
)
openrouter_client = AsyncOpenAI(
    api_key=settings.openrouter_api_key or "unset",
    base_url="https://openrouter.ai/api/v1",
)

Provider = tuple[str, AsyncOpenAI, str]  # (name, client, model)


def default_primary_model() -> str:
    """Model the active primary provider should use when none is specified."""
    if settings.llm_provider == "local":
        return settings.local_llm_model
    return GROQ_DEFAULT_MODEL


def default_summary_model() -> str:
    """Cheap model for short classification/summary calls."""
    if settings.llm_provider == "local":
        return settings.local_llm_summary_model or settings.local_llm_model
    return GROQ_SUMMARY_MODEL


def provider_chain(
    primary_model: str | None = None,
    fallback_model: str = OPENROUTER_DEFAULT_MODEL,
    *,
    summary: bool = False,
) -> list[Provider]:
    """Ordered list of providers to try for a completion.

    ``primary_model`` is the model for the *primary* provider. Fallback cloud
    providers use their own sensible defaults (a Groq model name means nothing
    to Ollama and vice versa). ``summary=True`` picks the cheap summary models.
    """
    if primary_model is None:
        primary_model = default_summary_model() if summary else default_primary_model()
    groq_fallback = GROQ_SUMMARY_MODEL if summary else GROQ_DEFAULT_MODEL

    chain: list[Provider] = []
    if settings.llm_provider == "local":
        chain.append(("local", local_client, primary_model))
        if settings.groq_api_key:
            chain.append(("groq", groq_client, groq_fallback))
    else:
        chain.append(("groq", groq_client, primary_model))
    if settings.openrouter_api_key:
        chain.append(("openrouter", openrouter_client, fallback_model))
    return chain


async def _complete(
    chain: list[Provider],
    messages: list[dict],
    *,
    temperature: float,
    max_tokens: int,
) -> str:
    """Try each provider in order; return the first successful completion."""
    last_error: Exception | None = None
    for name, client, model in chain:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001 — any provider error → next provider
            last_error = e
            log.warning("LLM provider %s (%s) failed: %s", name, model, e)
    raise RuntimeError(
        f"All LLM providers failed ({', '.join(n for n, _, _ in chain)})"
    ) from last_error


async def chat(
    user_prompt: str,
    *,
    system_prompt: str | None = None,
    model: str | None = None,
    fallback_model: str = OPENROUTER_DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    summary: bool = False,
) -> str:
    """One chat completion through the provider chain.

    ``model=None`` resolves to the active provider's default (or its cheap
    summary model when ``summary=True``).
    """
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return await _complete(
        provider_chain(model, fallback_model, summary=summary),
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


if __name__ == "__main__":
    print("LLM (core):")
    print(f"  provider: {settings.llm_provider}")
    print("  chat chain:    " + " -> ".join(f"{n}:{m}" for n, _, m in provider_chain()))
    print("  summary chain: " + " -> ".join(f"{n}:{m}" for n, _, m in provider_chain(summary=True)))
    print("  chat(user_prompt, system_prompt=?, model=?, ...) -> str")
    print("LLM module OK")
