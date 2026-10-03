"""Re-chunk and re-tag every stored original: `python -m docfactory.ingest.chunk_rebuild`.

Use it after the chunkers or the ontology signals change. Chunks and rule tags are rewritten from the files in DocStore/; the DocStore
row (hash, version) is unchanged. LLM-fallback tags are not reproduced (rerun ingestion of the file for those). A row whose file is
missing on disk is reported and left alone.
"""
import sys

from docfactory import db
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.paths import docstore_dir
from docfactory.ingest.tagging import tag_chunks
from docfactory.ontology.signals import load_signals


def rebuild_chunks() -> dict[str, str]:
    """Path -> outcome ('N chunks, M tags', 'missing on disk' or the error)."""
    signals = load_signals()
    outcomes = {}
    for row in db.list_docstore_rows():
        path = docstore_dir() / row["FullPath"]
        if not path.is_file():
            outcomes[row["FullPath"]] = "missing on disk"
            continue
        try:
            chunks = chunk_file(path)
        except Exception as error:
            outcomes[row["FullPath"]] = f"could not chunk: {error}"
            continue
        tags, _ = tag_chunks(chunks, signals)
        db.commit_ingested(row["FullPath"], row["Hashcode"], row["Timestamp"],
                           [(c.chunk_no, c.heading, c.page_from, c.page_to, c.text, c.text_hash) for c in chunks],
                           [(t.chunk_no, t.entity, t.origin, t.score, t.evidence) for t in tags])
        outcomes[row["FullPath"]] = f"{len(chunks)} chunks, {len(tags)} tags"
    return outcomes


def main(argv: list[str] | None = None) -> int:
    outcomes = rebuild_chunks()
    for path, outcome in outcomes.items():
        print(f"{path}: {outcome}")
    if not outcomes:
        print("DocStore is empty")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
