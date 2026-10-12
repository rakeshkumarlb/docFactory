"""Pack one entity's tagged chunks into small batches for the extraction calls (Phase 3). Deterministic, no LLM.

A batch is a run of whole chunks in document order whose text stays within a character budget; a chunk is never split (ingestion
already caps chunks at 4000 characters). The chunks hash identifies what an entity's extraction from a file was based on, so an
unchanged entity can be skipped without an LLM call.
"""
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.doc_chunk import DocChunk

BATCH_CHARS = 3500  # live: 6000-character batches dense with requirement rows overflowed one reply


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


MIN_SPLIT_LINES = 4  # a chunk with fewer lines is not split


def split_chunk(chunk: DocChunk) -> list[DocChunk]:
    """The chunk cut in two at a line boundary near the middle, or [chunk] when it is too short to cut.

    The cheap last resort for a single chunk whose answer the model cannot deliver (a table of many rows can be too long to return as one
    tool call): both halves keep the chunk number and heading, and when the first line is a table header (cells joined with ' | ') the
    second half starts with it again, so its rows keep their column names.
    """
    lines = chunk.text.splitlines()
    if len(lines) < MIN_SPLIT_LINES:
        return [chunk]
    middle = len(lines) // 2
    header = [lines[0]] if " | " in lines[0] and middle > 1 else []
    return [chunk.model_copy(update={"text": "\n".join(lines[:middle])}), chunk.model_copy(update={"text": "\n".join(header + lines[middle:])})]


def batch_text(batch: list[DocChunk]) -> str:
    """The text the model sees for one batch: each chunk as '[chunk N] <heading trail>' followed by its text."""
    return "\n\n".join(f"[chunk {c.chunk_no}] {c.heading}\n{c.text}" for c in batch)


def chunks_hash(chunks: list[DocChunk]) -> str:
    """SHA-256 over the headings and texts of the chunks in chunk order: changes exactly when what the entity was extracted from changes."""
    ordered = sorted(chunks, key=lambda c: c.chunk_no)
    return sha256_hex(canonical_json([[c.heading, c.text] for c in ordered]))
