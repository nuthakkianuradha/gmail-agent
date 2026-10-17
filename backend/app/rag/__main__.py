"""`uv run python -m app.rag` — walk the pipeline end to end:
load → chunk → embed → store(skipped: no writes) → retrieve, against the live DB."""

from app.rag import load, chunk, embed, retrieve
from app.rag.learn import DIFF_SUMMARY_PROMPT

print("RAG subsystem — pipeline walk-through")
doc = load.load_email({"id": "demo", "subject": "Lunch Thursday?", "body_text": "Are you free at noon?"})
print(f"  1 load:     {doc.source_type}/{doc.source_id} -> {doc.text!r}")
chunks = chunk.chunk(doc)
print(f"  2 chunk:    {len(chunks)} chunk(s), max {chunk.MAX_CHARS} chars, overlap {chunk.OVERLAP}")
vecs = embed.encode_batch([c.text for c in chunks])
print(f"  3 embed:    {len(vecs)} x {len(vecs[0])}-dim via {embed.MODEL_NAME} (local)")
print(f"  4 store:    (skipped — would delete+insert {len(chunks)} row(s) in `embeddings`)")
print(f"  5 index:    = load -> chunk -> embed -> store")
rows = retrieve.retrieve_context("00000000-0000-0000-0000-000000000000", doc.text, match_count=1)
print(f"  6 retrieve: match_embeddings() reachable -> {len(rows)} rows for a nonexistent user")
print(f"  7 learn:    DIFF_SUMMARY_PROMPT has {DIFF_SUMMARY_PROMPT.count('{')} placeholders")
print("RAG subsystem OK")
