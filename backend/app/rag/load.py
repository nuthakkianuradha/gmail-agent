"""RAG stage 1 — **LOAD**.

Turn a raw record into a :class:`Document`: the text we want to be findable
later, plus metadata that rides along in the row. Every source type has one
loader. This is the only place that knows the shape of the source records.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Document:
    source_type: str          # email | rule | persona | modification
    source_id: str            # the row id in the source table
    text: str                 # what gets chunked + embedded
    metadata: dict = field(default_factory=dict)


def email_text(email_data: dict) -> str:
    """Canonical text form of an email. Also used as the *query* at retrieval
    time, so an incoming email and a stored one are embedded the same way."""
    return f"Subject: {email_data.get('subject', '')}\n{email_data.get('body_text', '')}"


def load_email(email_record: dict) -> Document:
    return Document(
        "email",
        email_record["id"],
        email_text(email_record),
        {
            "direction": email_record.get("direction", "inbound"),
            "subject": email_record.get("subject", ""),
            "from_address": email_record.get("from_address", ""),
        },
    )


def load_rule(rule_id: str, rule_text: str) -> Document:
    return Document("rule", rule_id, rule_text)


def load_persona(persona_id: str, persona: dict) -> Document:
    text = (
        f"Tone: {persona.get('tone', '')}\n"
        f"Style: {persona.get('style_notes', '')}\n"
        f"Instructions: {persona.get('custom_instructions', '')}"
    )
    return Document("persona", persona_id, text)


def load_modification(
    modification_id: str,
    snippet: str,
    draft_before: str,
    draft_after: str,
    diff_summary: str,
) -> Document:
    text = (
        f"Original email: {snippet}\n"
        f"AI draft: {draft_before[:500]}\n"
        f"User edited to: {draft_after[:500]}\n"
        f"Change summary: {diff_summary}"
    )
    return Document("modification", modification_id, text, {"diff_summary": diff_summary})


if __name__ == "__main__":
    doc = load_email({"id": "e1", "subject": "Lunch?", "body_text": "Free Thursday?", "direction": "inbound"})
    print("LOAD: record -> Document")
    print(f"  {doc}")
    print(f"  loaders: load_email, load_rule, load_persona, load_modification")
    print("Load module OK")
