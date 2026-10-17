"""RAG stage 3 — **EMBED**.

Text → 768-dim unit vector, computed **locally** with sentence-transformers
``all-mpnet-base-v2``. No API, no cost, no network after the one-time model
download (~420 MB). Vectors are L2-normalized so cosine similarity is just a
dot product, which is what the pgvector HNSW index (``vector_cosine_ops``) uses.

The model is loaded lazily once per process.
"""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-mpnet-base-v2"
DIMENSIONS = 768  # must match `embedding vector(768)` in the schema

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def encode(text: str) -> list[float]:
    """Embed one text."""
    return _get_model().encode(text, normalize_embeddings=True).tolist()


def encode_batch(texts: list[str]) -> list[list[float]]:
    """Embed many texts at once (much faster than a loop over ``encode``)."""
    if not texts:
        return []
    vecs = _get_model().encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vecs]


if __name__ == "__main__":
    print(f"EMBED: text -> {DIMENSIONS}-dim vector via {MODEL_NAME} (local)")
    vec = encode("Hello, this is a test email about project updates.")
    print(f"  dims={len(vec)}  first 3={[round(x, 4) for x in vec[:3]]}")
    vecs = encode_batch(["Email one", "Email two", "Email three"])
    print(f"  batch: {len(vecs)} vectors")
    assert len(vec) == DIMENSIONS
    print("Embed module OK")
