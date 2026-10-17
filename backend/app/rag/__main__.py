"""`uv run python -m app.rag` — smoke-check the memory subsystem end to end
(local embedding model + Supabase reachability + vector search)."""

from app.rag.embeddings import encode
from app.rag.retrieval import retrieve_context, DEFAULT_PERSONA
from app.rag.indexing import email_to_text
from app.rag.learning import DIFF_SUMMARY_PROMPT

print("RAG subsystem")
vec = encode("Hello, this is a test email about project updates.")
print(f"  embeddings: all-mpnet-base-v2 -> {len(vec)} dims (local)")
print(f"  indexing:   email_to_text -> {email_to_text({'subject': 'Hi', 'body_text': 'Hello'})!r}")
rows = retrieve_context("00000000-0000-0000-0000-000000000000", "hello", match_count=1)
print(f"  retrieval:  match_embeddings() reachable -> {len(rows)} rows for a nonexistent user")
print(f"  learning:   DIFF_SUMMARY_PROMPT has {DIFF_SUMMARY_PROMPT.count('{')} placeholders")
print(f"  default persona tone: {DEFAULT_PERSONA['tone']}")
print("RAG subsystem OK")
