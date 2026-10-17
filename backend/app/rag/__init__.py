"""RAG = the agent's **memory**: embed, store, retrieve, and learn.

One unified ``embeddings`` table in Supabase (pgvector, 768-dim, HNSW cosine)
holds every indexable thing, discriminated by ``source_type``:
``email`` | ``rule`` | ``modification`` | ``persona``.

- ``embeddings`` — text → 768-dim vector, locally (sentence-transformers).
- ``indexing``   — WRITE side: ``index_email / index_rule / index_persona / index_modification``.
- ``retrieval``  — READ side: vector search (``retrieve_context``) + persona/rules reads.
- ``learning``   — the feedback loop after every send: archive the sent email and
                   record the user's edit (with an LLM diff summary), both indexed.

Depends on ``core.db`` and (for the diff summary) ``core.llm``. Knows nothing
about Gmail/MCP or the agent's prompts.
"""
