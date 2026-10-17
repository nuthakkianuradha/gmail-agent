"""RAG **retrieval** — the read side of memory.

``retrieve_context`` embeds the incoming email and asks Postgres (pgvector) for
the nearest neighbours via the ``match_embeddings`` SQL function, filtered to
this user and the requested ``source_types``. ``get_persona`` /
``get_active_rules`` are the non-vector reads the agent also needs.
"""

from app.core.db import get_supabase
from app.rag.embeddings import encode

DEFAULT_PERSONA = {
    "display_name": "",
    "tone": "professional",
    "style_notes": "",
    "signature": "",
    "custom_instructions": "",
}


def retrieve_context(
    user_id: str,
    query_text: str,
    match_count: int = 8,
    match_threshold: float = 0.4,
    source_types: list[str] | tuple[str, ...] = ("email", "modification"),
) -> list[dict]:
    """Vector search: rows with ``similarity = 1 - cosine_distance`` ≥ threshold."""
    result = get_supabase().rpc(
        "match_embeddings",
        {
            "query_embedding": encode(query_text),
            "query_user_id": user_id,
            "filter_source_types": list(source_types),
            "match_threshold": match_threshold,
            "match_count": match_count,
        },
    ).execute()
    return result.data or []


def get_persona(user_id: str) -> dict:
    """The user's persona row, or a sensible default if they have none yet."""
    result = get_supabase().table("personas").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else dict(DEFAULT_PERSONA)


def get_active_rules(user_id: str) -> list[dict]:
    """Active rules, highest priority first."""
    result = (
        get_supabase()
        .table("rules")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("priority", desc=True)
        .execute()
    )
    return result.data or []


if __name__ == "__main__":
    print("RAG retrieval (read side):")
    print("  retrieve_context(user_id, query_text, match_count=8, match_threshold=0.4, source_types=(email, modification))")
    print("  get_persona(user_id) -> dict   (default:", DEFAULT_PERSONA["tone"], ")")
    print("  get_active_rules(user_id) -> list[dict]")
    print("RAG retrieval module OK")
