"""RAG stage 4 — **STORE**.

Write chunk vectors into the one ``embeddings`` table (Supabase Postgres +
pgvector). A source (one email, one rule, …) may own several rows — one per
chunk — so re-indexing a source first deletes its old rows, then inserts the
new ones. Without that, every persona save would add another stale vector.

Columns: user_id, source_type, source_id, content_text, embedding vector(768),
metadata jsonb. The HNSW cosine index on ``embedding`` is created by the
migration, not here.
"""

from app.core.db import get_supabase
from app.rag.chunk import Chunk

TABLE = "embeddings"


def delete_source(user_id: str, source_type: str, source_id: str) -> None:
    """Remove every chunk row belonging to one source record."""
    (
        get_supabase().table(TABLE).delete()
        .eq("user_id", user_id)
        .eq("source_type", source_type)
        .eq("source_id", source_id)
        .execute()
    )


def store_chunks(user_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> int:
    """Replace a source's rows with these chunks. Returns rows written."""
    if not chunks:
        return 0
    doc = chunks[0].doc
    delete_source(user_id, doc.source_type, doc.source_id)
    rows = [
        {
            "user_id": user_id,
            "source_type": c.doc.source_type,
            "source_id": c.doc.source_id,
            "content_text": c.text,
            "embedding": v,
            "metadata": {**c.doc.metadata, "chunk_index": c.index, "chunk_count": len(chunks)},
        }
        for c, v in zip(chunks, vectors, strict=True)
    ]
    get_supabase().table(TABLE).insert(rows).execute()
    return len(rows)


if __name__ == "__main__":
    print(f"STORE: [Chunk] + [vector] -> rows in `{TABLE}` (delete-then-insert per source)")
    print("  store_chunks(user_id, chunks, vectors) -> int")
    print("  delete_source(user_id, source_type, source_id)")
    print("Store module OK")
