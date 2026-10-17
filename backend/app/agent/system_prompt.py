"""Agent block: **system prompt**.

The agent's standing instructions to the model — its role and hard constraints.
This is the canonical (and only) home of the reply system prompt.
"""

REPLY_SYSTEM_PROMPT = """You are an email reply assistant. Draft a reply to the email below.
Follow the user's persona, rules, and learned preferences exactly.
Write ONLY the reply body — no subject line, no headers, no meta-commentary.
Plain text only: no markdown, no bullet syntax, no code fences.
If no signature is set, close with a simple sign-off (e.g. "Best regards,") and nothing else —
never invent a name and never write placeholders like "(no signature provided)"."""


def build_system_prompt() -> str:
    """Return the system prompt for the reply agent.

    A function (rather than a bare constant) so future variants — e.g. per-tone
    or per-locale system prompts — can be assembled here without changing callers.
    """
    return REPLY_SYSTEM_PROMPT


if __name__ == "__main__":
    print("Reply agent system prompt:")
    print(build_system_prompt())
    print("System prompt module OK")
