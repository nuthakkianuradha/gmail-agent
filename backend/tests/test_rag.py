"""RAG pipeline stages, no model and no DB: load, chunk, index (embed/store faked), retrieve dedupe."""

from app.rag import index as index_mod
from app.rag.chunk import Chunk, chunk, chunk_text
from app.rag.load import Document, email_text, load_email, load_modification, load_persona, load_rule
from app.rag.retrieve import _best_chunk_per_source


def test_load_builds_documents_with_source_identity():
    e = load_email({"id": "e1", "subject": "Hi", "body_text": "Body", "direction": "outbound", "from_address": "me@x"})
    assert (e.source_type, e.source_id) == ("email", "e1")
    assert e.text == "Subject: Hi\nBody" == email_text({"subject": "Hi", "body_text": "Body"})
    assert e.metadata["direction"] == "outbound"
    assert load_rule("r1", "Be brief").text == "Be brief"
    assert "Tone: warm" in load_persona("p1", {"tone": "warm"}).text
    m = load_modification("m1", "snip", "before", "after", "shorter")
    assert m.source_type == "modification" and "shorter" in m.text


def test_short_text_is_one_chunk_and_empty_is_none():
    assert chunk_text("short") == ["short"]
    assert chunk_text("   ") == []


def test_long_text_is_split_with_overlap():
    paras = [f"P{i} " + "word " * 50 for i in range(10)]
    text = "\n\n".join(paras)
    pieces = chunk_text(text, max_chars=600, overlap=60)
    assert len(pieces) > 1
    assert all(len(p) <= 600 for p in pieces)
    assert "".join(pieces).count("P0 ") == 1 and any("P9 " in p for p in pieces)
    # overlap: the tail of chunk i reappears at the head of chunk i+1
    assert pieces[1].startswith(pieces[0][-60:])


def test_single_oversized_paragraph_is_hard_split():
    pieces = chunk_text("x" * 3000, max_chars=1000, overlap=100)
    assert len(pieces) >= 3 and all(len(p) <= 1000 for p in pieces)


def test_chunk_objects_keep_document_and_position():
    doc = Document("email", "e1", "\n\n".join("para " * 100 for _ in range(5)))
    cs = chunk(doc, max_chars=800, overlap=50)
    assert [c.index for c in cs] == list(range(len(cs)))
    assert all(c.doc is doc for c in cs)


def test_index_runs_load_chunk_embed_store(monkeypatch):
    seen = {}
    monkeypatch.setattr(index_mod, "encode_batch", lambda texts: [[0.1] * 3 for _ in texts])

    def fake_store(user_id, chunks, vectors):
        seen["user_id"], seen["chunks"], seen["vectors"] = user_id, chunks, vectors
        return len(chunks)

    monkeypatch.setattr(index_mod, "store_chunks", fake_store)
    n = index_mod.index_rule("u1", "r1", "Always sign off with Best")
    assert n == 1 and seen["user_id"] == "u1"
    assert isinstance(seen["chunks"][0], Chunk) and seen["chunks"][0].doc.source_id == "r1"
    assert len(seen["vectors"]) == 1


def test_retrieve_collapses_chunks_to_best_per_source():
    rows = [
        {"source_type": "email", "source_id": "a", "similarity": 0.9},
        {"source_type": "email", "source_id": "a", "similarity": 0.7},
        {"source_type": "modification", "source_id": "a", "similarity": 0.65},
        {"source_type": "email", "source_id": "b", "similarity": 0.6},
    ]
    out = _best_chunk_per_source(rows)
    assert [(r["source_type"], r["source_id"], r["similarity"]) for r in out] == [
        ("email", "a", 0.9), ("modification", "a", 0.65), ("email", "b", 0.6)]
