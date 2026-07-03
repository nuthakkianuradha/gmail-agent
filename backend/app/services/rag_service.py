from app.db.supabase_client import get_supabase
from app.services.embedding_service import encode


def index_email(user_id: str, email_data: dict) -> None:
    """Embed and store an email in the embeddings table."""
    supabase = get_supabase()
    content = f"Subject: {email_data.get('subject', '')}\n{email_data.get('body_text', '')}"
    content = content[:1500]  # Truncate for embedding model limits
    embedding = encode(content)

    supabase.table("embeddings").upsert(
        {
            "user_id": user_id,
            "source_type": "email",
            "source_id": email_data["id"],
            "content_text": content,
            "embedding": embedding,
            "metadata": {
                "direction": email_data.get("direction", "inbound"),
                "subject": email_data.get("subject", ""),
                "from_address": email_data.get("from_address", ""),
            },
        },
        on_conflict="id",
    ).execute()


def index_rule(user_id: str, rule_id: str, rule_text: str) -> None:
    """Embed and store a rule."""
    supabase = get_supabase()
    embedding = encode(rule_text)

    supabase.table("embeddings").upsert(
        {
            "user_id": user_id,
            "source_type": "rule",
            "source_id": rule_id,
            "content_text": rule_text,
            "embedding": embedding,
        },
        on_conflict="id",
    ).execute()


def index_modification(
    user_id: str,
    modification_id: str,
    snippet: str,
    draft_before: str,
    draft_after: str,
    diff_summary: str,
) -> None:
    """Embed and store a modification."""
    supabase = get_supabase()
    content = (
        f"Original email: {snippet}\n"
        f"AI draft: {draft_before[:500]}\n"
        f"User edited to: {draft_after[:500]}\n"
        f"Change summary: {diff_summary}"
    )
    embedding = encode(content)

    supabase.table("embeddings").upsert(
        {
            "user_id": user_id,
            "source_type": "modification",
            "source_id": modification_id,
            "content_text": content,
            "embedding": embedding,
        },
        on_conflict="id",
    ).execute()


def index_persona(user_id: str, persona_id: str, persona: dict) -> None:
    """Embed and store persona."""
    supabase = get_supabase()
    content = (
        f"Tone: {persona.get('tone', '')}\n"
        f"Style: {persona.get('style_notes', '')}\n"
        f"Instructions: {persona.get('custom_instructions', '')}"
    )
    embedding = encode(content)

    supabase.table("embeddings").upsert(
        {
            "user_id": user_id,
            "source_type": "persona",
            "source_id": persona_id,
            "content_text": content,
            "embedding": embedding,
        },
        on_conflict="id",
    ).execute()


def retrieve_context(
    user_id: str,
    email_text: str,
    match_count: int = 8,
    match_threshold: float = 0.4,
    source_types: list[str] | tuple[str, ...] = ("email", "modification"),
) -> list[dict]:
    """Vector search for similar emails and modifications."""
    supabase = get_supabase()
    query_embedding = encode(email_text)

    result = supabase.rpc(
        "match_embeddings",
        {
            "query_embedding": query_embedding,
            "query_user_id": user_id,
            "filter_source_types": list(source_types),
            "match_threshold": match_threshold,
            "match_count": match_count,
        },
    ).execute()

    return result.data or []


def get_persona(user_id: str) -> dict:
    """Fetch the user's persona."""
    supabase = get_supabase()
    result = supabase.table("personas").select("*").eq("user_id", user_id).execute()
    if result.data:
        return result.data[0]
    return {
        "display_name": "",
        "tone": "professional",
        "style_notes": "",
        "signature": "",
        "custom_instructions": "",
    }


def get_active_rules(user_id: str) -> list[dict]:
    """Fetch all active rules for a user."""
    supabase = get_supabase()
    result = (
        supabase.table("rules")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("priority", desc=True)
        .execute()
    )
    return result.data or []


if __name__ == "__main__":
    print("RAG service functions (memory store + retrieval):")
    print("  index_email(user_id, email_data)")
    print("  index_rule(user_id, rule_id, rule_text)")
    print("  index_modification(user_id, mod_id, snippet, before, after, summary)")
    print("  index_persona(user_id, persona_id, persona)")
    print("  retrieve_context(user_id, email_text, match_count, match_threshold, source_types)")
    print("  get_persona(user_id) / get_active_rules(user_id)")
    print("  (prompt assembly now lives in app.agent.state + app.agent.input)")
    print("RAG service module OK")
