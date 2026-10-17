"""RAG **indexing** — the write side of memory.

Every ``index_*`` function turns one record into text, embeds it, and upserts a
row into the unified ``embeddings`` table with the right ``source_type``.
"""

from app.core.db import get_supabase
from app.rag.embeddings import encode


def _upsert(user_id: str, source_type: str, source_id: str, content: str, metadata: dict | None = None) -> None:
    row = {
        "user_id": user_id,
        "source_type": source_type,
        "source_id": source_id,
        "content_text": content,
        "embedding": encode(content),
    }
    if metadata is not None:
        row["metadata"] = metadata
    get_supabase().table("embeddings").upsert(row, on_conflict="id").execute()


def email_to_text(email_data: dict) -> str:
    """Canonical text form of an email for embedding (also used as the query)."""
    text = f"Subject: {email_data.get('subject', '')}\n{email_data.get('body_text', '')}"
    return text[:1500]  # embedding-model input limit


def index_email(user_id: str, email_data: dict) -> None:
    """Embed and store an email (sent or received)."""
    _upsert(
        user_id, "email", email_data["id"], email_to_text(email_data),
        metadata={
            "direction": email_data.get("direction", "inbound"),
            "subject": email_data.get("subject", ""),
            "from_address": email_data.get("from_address", ""),
        },
    )


def index_rule(user_id: str, rule_id: str, rule_text: str) -> None:
    """Embed and store a user rule."""
    _upsert(user_id, "rule", rule_id, rule_text)


def index_persona(user_id: str, persona_id: str, persona: dict) -> None:
    """Embed and store the user's persona."""
    content = (
        f"Tone: {persona.get('tone', '')}\n"
        f"Style: {persona.get('style_notes', '')}\n"
        f"Instructions: {persona.get('custom_instructions', '')}"
    )
    _upsert(user_id, "persona", persona_id, content)


def modification_to_text(snippet: str, draft_before: str, draft_after: str, diff_summary: str) -> str:
    return (
        f"Original email: {snippet}\n"
        f"AI draft: {draft_before[:500]}\n"
        f"User edited to: {draft_after[:500]}\n"
        f"Change summary: {diff_summary}"
    )


def index_modification(
    user_id: str,
    modification_id: str,
    snippet: str,
    draft_before: str,
    draft_after: str,
    diff_summary: str,
) -> None:
    """Embed and store a user edit (draft before/after + summary)."""
    _upsert(
        user_id, "modification", modification_id,
        modification_to_text(snippet, draft_before, draft_after, diff_summary),
    )


if __name__ == "__main__":
    print("RAG indexing (write side):")
    print("  index_email(user_id, email_data)")
    print("  index_rule(user_id, rule_id, rule_text)")
    print("  index_persona(user_id, persona_id, persona)")
    print("  index_modification(user_id, mod_id, snippet, before, after, summary)")
    print("  sample email text:", repr(email_to_text({"subject": "Hi", "body_text": "Hello"})))
    print("RAG indexing module OK")
