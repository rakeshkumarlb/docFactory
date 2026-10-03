"""Read-only access to what ingestion stored: DocStore rows and the chunked text of a stored original (no file is opened)."""
from docfactory import db
from docfactory.ingest.paths import docstore_dir, resolve_within


def _normal(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def search_docstore(folder: str | None = None, name_contains: str | None = None) -> list[dict]:
    """DocStore rows (FullPath, Hashcode, Version, Timestamp) filtered by folder and/or file-name text. Read-only."""
    return db.list_docstore_rows(folder=_normal(folder) if folder else None, name_contains=name_contains)


def read_docstore_text(path: str) -> str:
    """The text of a stored original, rebuilt from its chunks: each chunk as '## <heading trail>' followed by its text.

    Raises ValueError for a bad path, FileNotFoundError when the file is not in DocStore or has no chunks.
    """
    relative = _normal(path)
    resolve_within(docstore_dir(), relative)  # rejects empty, absolute and escaping paths
    if db.get_docstore_row(relative) is None:
        raise FileNotFoundError(f"no such file in DocStore: {path}; use list_docstore to see what is stored")
    chunks = db.list_doc_chunks(relative)
    if not chunks:
        raise FileNotFoundError(f"{path} has no chunks; run python -m docfactory.ingest.chunk_rebuild")
    return "\n\n".join(f"## {chunk['Heading']}\n{chunk['Text']}" for chunk in chunks)
