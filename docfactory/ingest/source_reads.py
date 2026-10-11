"""Read-only access to what ingestion stored: the Source concepts of the bundle and the text of a stored original (rebuilt from its chunks)."""
from docfactory.bundle.paths import resolve_in
from docfactory.bundle.source_store import SourceStore
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.chunks_out_of_date_error import ChunksOutOfDateError
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.source_record import SourceRecord


def _normal(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def search_sources(folder: str | None = None, name_contains: str | None = None) -> list[SourceRecord]:
    """The Sources (path, hash, version) filtered by scope folder and/or path text, ordered by path. Read-only."""
    records = SourceStore().list(_normal(folder) if folder else None)
    return [r for r in records if not name_contains or name_contains.lower() in r.path.lower()]


def read_chunks(path: str) -> tuple[SourceRecord, list[DocChunk]]:
    """The Source of the stored original `path` and its chunks, re-derived from the file and checked against the Source's outline.

    Raises ValueError for a bad path, FileNotFoundError when there is no Source or no original, ChunksOutOfDateError when the chunks differ.
    """
    relative = _normal(path)
    resolve_in(SourceStore().root, relative)  # rejects escaping paths
    store = SourceStore()
    record = store.read(relative)
    if record is None:
        raise FileNotFoundError(f"no such file in the bundle: {path}; use search_sources to see what is stored")
    original = store.original(relative)
    if not original.is_file():
        raise FileNotFoundError(f"the original of {path} is missing on disk; ingest the file again")
    chunks = chunk_file(original)
    if [(c.chunk_no, c.text_hash) for c in chunks] != [(c.chunk_no, c.text_hash) for c in record.chunks]:
        raise ChunksOutOfDateError(f"{path} no longer chunks as it did at ingestion; run python -m docfactory.ingest.chunk_rebuild")
    return record, chunks


def read_source_text(path: str) -> str:
    """The text of a stored original, rebuilt from its chunks: each chunk as '## <heading trail>' followed by its text."""
    _, chunks = read_chunks(path)
    return "\n\n".join(f"## {chunk.heading}\n{chunk.text}" for chunk in chunks)
