"""RAG stage 2 — **CHUNK**.

Embedding models have an input limit (all-mpnet-base-v2 reads ~384 tokens;
anything past that is silently ignored), and one vector per *idea* retrieves
better than one vector per *document*. So long text is split into overlapping
pieces. Short text (rules, personas, most emails) stays as a single chunk.

Strategy: split on paragraph breaks, pack paragraphs up to ``max_chars``, and
carry ``overlap`` characters from the end of one chunk into the start of the
next so a sentence straddling a boundary is still findable.
"""

from dataclasses import dataclass

from app.rag.load import Document

MAX_CHARS = 1200   # ≈ 300 tokens of English — safely under the model's window
OVERLAP = 150


@dataclass(frozen=True)
class Chunk:
    doc: Document
    index: int        # 0-based position within the document
    text: str


def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        # A single paragraph longer than max_chars is hard-split.
        while len(para) > max_chars:
            head, para = para[:max_chars], para[max_chars - overlap:]
            if current:
                chunks.append(current)
                current = ""
            chunks.append(head)
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + para if overlap else para
    if current:
        chunks.append(current)
    return chunks


def chunk(doc: Document, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[Chunk]:
    return [Chunk(doc, i, t) for i, t in enumerate(chunk_text(doc.text, max_chars, overlap))]


if __name__ == "__main__":
    short = Document("rule", "r1", "Always be concise.")
    long = Document("email", "e1", "\n\n".join(f"Paragraph {i}: " + "word " * 60 for i in range(8)))
    print("CHUNK: Document -> [Chunk]")
    print(f"  short rule  -> {len(chunk(short))} chunk")
    cs = chunk(long)
    print(f"  long email ({len(long.text)} chars) -> {len(cs)} chunks of {[len(c.text) for c in cs]} chars")
    print("Chunk module OK")
