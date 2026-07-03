from openai import AsyncOpenAI
from app.config import get_settings
from app.utils.prompt_templates import DIFF_SUMMARY_PROMPT

settings = get_settings()

groq_client = AsyncOpenAI(
    api_key=settings.groq_api_key,
    base_url="https://api.groq.com/openai/v1",
)

openrouter_client = AsyncOpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)


async def generate_draft(
    system_prompt: str,
    user_prompt: str,
    *,
    primary_model: str = "llama-3.3-70b-versatile",
    fallback_model: str = "google/gemini-2.0-flash-001",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Generate an email draft. Tries Groq first, falls back to OpenRouter.

    Model choices and sampling are supplied by the agent's ``AgentConfig`` (see
    :mod:`app.agent.config`); the defaults here mirror that config so the
    function is still usable standalone.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await groq_client.chat.completions.create(
            model=primary_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except Exception:
        # Fallback to OpenRouter
        response = await openrouter_client.chat.completions.create(
            model=fallback_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


async def summarize_diff(draft_before: str, draft_after: str) -> str:
    """Summarize what the user changed in their edit."""
    prompt = DIFF_SUMMARY_PROMPT.format(
        draft_before=draft_before[:1000],
        draft_after=draft_after[:1000],
    )

    try:
        response = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content or ""
    except Exception:
        return "User modified the draft."


if __name__ == "__main__":
    print("LLM service configured:")
    print(f"  Groq client: {groq_client.base_url}")
    print(f"  OpenRouter client: {openrouter_client.base_url}")
    print("  generate_draft(system_prompt, user_prompt) -> str")
    print("  summarize_diff(draft_before, draft_after) -> str")
    print("LLM service module OK")
