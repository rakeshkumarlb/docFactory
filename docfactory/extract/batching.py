"""Pack one entity's tagged chunks into small batches for the extraction calls (Phase 3). Deterministic, no LLM.

A batch is a run of whole chunks in document order whose text stays within a character budget; a chunk is never split (ingestion
already caps chunks at 4000 characters). The chunks hash identifies what an entity's extraction from a file was based on, so an
unchanged entity can be skipped without an LLM call.
"""
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.doc_chunk import DocChunk

BATCH_CHARS = 6000


def batch_chunks(chunks: list[DocChunk], budget: int = BATCH_CHARS) -> list[list[DocChunk]]:
    """The chunks (sorted by chunk number) in consecutive batches of at most `budget` text characters; an oversized chunk is a batch of its own."""
    batches: list[list[DocChunk]] = []
    size = 0
    for chunk in sorted(chunks, key=lambda c: c.chunk_no):
        length = len(chunk.text)
        if batches and size + length <= budget:
            batches[-1].append(chunk)
            size += length
        else:
            batches.append([chunk])
            size = length
    return batches


def batch_text(batch: list[DocChunk]) -> str:
    """The text the model sees for one batch: each chunk as '[chunk N] <heading trail>' followed by its text."""
    return "\n\n".join(f"[chunk {c.chunk_no}] {c.heading}\n{c.text}" for c in batch)


def chunks_hash(chunks: list[DocChunk]) -> str:
    """SHA-256 over the headings and texts of the chunks in chunk order: changes exactly when what the entity was extracted from changes."""
    ordered = sorted(chunks, key=lambda c: c.chunk_no)
    return sha256_hex(canonical_json([[c.heading, c.text] for c in ordered]))
