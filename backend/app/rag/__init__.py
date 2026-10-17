"""RAG = the agent's **memory**, written as the classic pipeline, one stage per file.

Read the files in this order:

    load.py      LOAD      a DB record (email / rule / persona / modification) → Document(text, metadata)
    chunk.py     CHUNK     long text → overlapping pieces that fit the embedding model
    embed.py     EMBED     text → 768-dim vector, locally (sentence-transformers all-mpnet-base-v2)
    store.py     STORE     vectors → rows in the one `embeddings` table (pgvector), keyed by source
    index.py     INDEX     the pipeline glue: load → chunk → embed → store  (index_email, index_rule, …)
    retrieve.py  RETRIEVE  query text → embed → match_embeddings() nearest-neighbour search → rows
    learn.py     LEARN     the feedback loop after every send: archive the sent mail, record the edit

One table, `embeddings`, holds everything with a `source_type` discriminator
(email | rule | modification | persona) and an HNSW cosine index.

Depends on ``core.db`` and (for the edit summary in ``learn``) ``core.llm``.
Knows nothing about Gmail/MCP or the agent's prompts.
"""
