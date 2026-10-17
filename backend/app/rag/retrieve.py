"""RAG stage 6 — **RETRIEVE**.

The read side. ``retrieve_context`` embeds the query the same way stored text
was embedded (same model, same normalization), then asks Postgres for the
nearest chunks via the ``match_embeddings`` SQL function:

    similarity = 1 - cosine_distance(embedding, query)   -- HNSW index
    where user_id = me and source_type in (...) and similarity > threshold
    order by distance limit match_count

Because a source can have several chunks, results are collapsed to one row per
source (its best chunk) so the prompt is not padded with near-duplicates.

``get_persona`` / ``get_active_rules`` are the plain (non-vector) reads the
agent's state block also needs.
"""

from app.core.db import get_supabase
from app.rag.embed import encode

DEFAULT_PERSONA = {
    "display_name": "",
    "tone": "professional",
    "style_notes": "",
    "signature": "",
    "custom_instructions": "",
}


def _best_chunk_per_source(rows: list[dict]) -> list[dict]:
    best: dict[tuple[str, str], dict] = {}
    for r in rows:  # rows arrive ordered by distance, so first seen is best
        best.setdefault((r["source_type"], r["source_id"]), r)
    return list(best.values())


def retrieve_context(
    user_id: str,
    query_text: str,
    match_count: int = 8,
    match_threshold: float = 0.4,
    source_types: list[str] | tuple[str, ...] = ("email", "modification"),
) -> list[dict]:
    """Nearest neighbours of ``query_text`` in this user's memory."""
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
    return _best_chunk_per_source(result.data or [])


def get_persona(user_id: str) -> dict:
    """The user's persona row, or a sensible default if they have none yet."""
    result = get_supabase().table("personas").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else dict(DEFAULT_PERSONA)


def get_active_rules(user_id: str) -> list[dict]:
    """Active rules, highest priority first."""
    result = (
        get_supabase().table("rules").select("*")
        .eq("user_id", user_id).eq("is_active", True)
        .order("priority", desc=True).execute()
    )
    return result.data or []


if __name__ == "__main__":
    print("RETRIEVE: query text -> embed -> match_embeddings() -> best chunk per source")
    print("  retrieve_context(user_id, query_text, match_count=8, match_threshold=0.4, source_types=(email, modification))")
    print("  get_persona(user_id) / get_active_rules(user_id)")
    rows = [{"source_type": "email", "source_id": "a", "similarity": 0.9},
            {"source_type": "email", "source_id": "a", "similarity": 0.7},
            {"source_type": "email", "source_id": "b", "similarity": 0.6}]
    print(f"  dedupe demo: {len(rows)} chunk rows -> {len(_best_chunk_per_source(rows))} sources")
    print("Retrieve module OK")
