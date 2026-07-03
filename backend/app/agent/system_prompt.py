"""Agent block: **system prompt**.

The agent's standing instructions to the model — its role and hard constraints.
This is the canonical home for the reply system prompt;
:mod:`app.utils.prompt_templates` re-exports it as ``DRAFT_SYSTEM_PROMPT`` for
backward compatibility.
"""

REPLY_SYSTEM_PROMPT = """You are an email reply assistant. Draft a reply to the email below.
Follow the user's persona, rules, and learned preferences exactly.
Write ONLY the reply body — no subject line, no headers, no meta-commentary."""


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
