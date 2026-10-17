"""RAG stage 5 — **INDEX**.

The pipeline glue: ``index(user_id, doc)`` runs **load → chunk → embed → store**
for one document. The ``index_*`` helpers below are what the rest of the app
calls; each one just picks the right loader.

    index_email(user_id, email_record)
    index_rule(user_id, rule_id, rule_text)
    index_persona(user_id, persona_id, persona)
    index_modification(user_id, modification_id, snippet, before, after, summary)
"""

from app.rag import load
from app.rag.chunk import chunk
from app.rag.embed import encode_batch
from app.rag.load import Document
from app.rag.store import store_chunks


def index(user_id: str, doc: Document) -> int:
    """Chunk, embed, and store one document. Returns rows written."""
    chunks = chunk(doc)
    vectors = encode_batch([c.text for c in chunks])
    return store_chunks(user_id, chunks, vectors)


def index_email(user_id: str, email_record: dict) -> int:
    return index(user_id, load.load_email(email_record))


def index_rule(user_id: str, rule_id: str, rule_text: str) -> int:
    return index(user_id, load.load_rule(rule_id, rule_text))


def index_persona(user_id: str, persona_id: str, persona: dict) -> int:
    return index(user_id, load.load_persona(persona_id, persona))


def index_modification(
    user_id: str,
    modification_id: str,
    snippet: str,
    draft_before: str,
    draft_after: str,
    diff_summary: str,
) -> int:
    return index(
        user_id,
        load.load_modification(modification_id, snippet, draft_before, draft_after, diff_summary),
    )


if __name__ == "__main__":
    print("INDEX: load -> chunk -> embed -> store")
    print("  index(user_id, Document) -> rows written")
    print("  index_email / index_rule / index_persona / index_modification")
    print("Index module OK")
