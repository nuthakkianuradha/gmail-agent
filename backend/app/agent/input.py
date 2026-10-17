"""Agent block: **input**.

Renders the agent's ``state`` plus the incoming email into the user-turn prompt
that goes to the model. This is the canonical (and only) home of the reply
input template.

Kept deliberately dependency-light: it accepts a duck-typed ``state`` object
(anything with ``persona``, ``rules``, ``past_emails``, ``modifications``) so it
never has to import the ``state`` module and risk an import cycle.
"""

REPLY_INPUT_TEMPLATE = """
USER PERSONA:
- Name: {display_name}
- Tone: {tone}
- Style: {style_notes}
- Signature: {signature}
- Instructions: {custom_instructions}
(Fields marked "(not set)" are simply unknown — never mention them in the reply
and never write placeholder text such as "(no signature provided)".)

RULES:
{rules_text}

RELEVANT PAST EMAILS (for context and style reference):
{past_emails_text}

LEARNED PREFERENCES (from past edits):
{modifications_text}

EMAIL TO REPLY TO:
From: {from_address}
Subject: {subject}
Body:
{body_text}

Draft a reply following the persona, rules, and learned preferences above.
"""


def _or_unset(value: str | None) -> str:
    """Empty persona fields become an explicit marker the prompt tells the model to ignore."""
    return value.strip() if value and value.strip() else "(not set)"


def _format_rules(rules: list[dict]) -> str:
    if not rules:
        return "(no rules set)"
    return "\n".join(f"- {r['rule_text']}" for r in rules)


def _format_past_emails(past_emails: list[dict]) -> str:
    if not past_emails:
        return "(no similar past emails found)"
    return "\n---\n".join(
        f"[similarity: {c['similarity']:.2f}]\n{c['content_text']}" for c in past_emails
    )


def _format_modifications(modifications: list[dict]) -> str:
    if not modifications:
        return "(no past modifications)"
    return "\n---\n".join(c["content_text"] for c in modifications)


def build_input(email_data: dict, state) -> str:
    """Render the user prompt from the incoming email and agent ``state``.

    ``state`` is any object exposing ``persona`` (dict), ``rules``,
    ``past_emails`` and ``modifications`` (lists) — typically an
    :class:`app.agent.state.AgentState`.
    """
    persona = state.persona or {}
    return REPLY_INPUT_TEMPLATE.format(
        display_name=_or_unset(persona.get("display_name")),
        tone=persona.get("tone") or "professional",
        style_notes=_or_unset(persona.get("style_notes")),
        signature=_or_unset(persona.get("signature")),
        custom_instructions=_or_unset(persona.get("custom_instructions")),
        rules_text=_format_rules(state.rules),
        past_emails_text=_format_past_emails(state.past_emails),
        modifications_text=_format_modifications(state.modifications),
        from_address=email_data.get("from_address", ""),
        subject=email_data.get("subject", ""),
        body_text=email_data.get("body_text", ""),
    )


if __name__ == "__main__":
    from types import SimpleNamespace

    fake_state = SimpleNamespace(
        persona={"display_name": "John", "tone": "professional", "signature": "Best, John"},
        rules=[{"rule_text": "Be concise"}],
        past_emails=[],
        modifications=[],
    )
    email = {"from_address": "client@example.com", "subject": "Update?", "body_text": "Any news?"}
    prompt = build_input(email, fake_state)
    print(prompt)
    print("Input module OK")
