from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-mpnet-base-v2")
    return _model


def encode(text: str) -> list[float]:
    """Encode a single text into a 768-dim embedding."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def encode_batch(texts: list[str]) -> list[list[float]]:
    """Encode multiple texts into embeddings."""
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return [e.tolist() for e in embeddings]


if __name__ == "__main__":
    print("Loading model...")
    vec = encode("Hello, this is a test email about project updates.")
    print(f"Embedding dimension: {len(vec)}")
    print(f"First 5 values: {vec[:5]}")

    vecs = encode_batch(["Email one", "Email two", "Email three"])
    print(f"Batch: {len(vecs)} embeddings, each dim {len(vecs[0])}")
    print("Embedding service OK")
