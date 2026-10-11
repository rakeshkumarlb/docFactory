"""Re-chunk and re-tag every stored original: `python -m docfactory.ingest.chunk_rebuild`.

Use it after the chunkers or the ontology signals change. The chunk outline and the rule tags of every Source concept are rewritten from
the originals in `<scope>/references/`; the hash and version are unchanged. LLM-fallback tags are not reproduced (ingest the file again
for those). A Source whose original is missing on disk is reported and left alone.
"""
import sys

from docfactory.bundle.source_store import SourceStore
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.tagging import tag_chunks
from docfactory.ontology.signals import load_signals


def rebuild_chunks() -> dict[str, str]:
    """Path -> outcome ('N chunks, M tags', 'missing on disk' or the error)."""
    signals = load_signals()
    store = SourceStore()
    outcomes = {}
    for record in store.list():
        path = store.original(record.path)
        if not path.is_file():
            outcomes[record.path] = "missing on disk"
            continue
        try:
            chunks = chunk_file(path)
        except Exception as error:
            outcomes[record.path] = f"could not chunk: {error}"
            continue
        tags, _ = tag_chunks(chunks, signals)
        store.write(record.path, record.hashcode, record.timestamp, chunks, tags)
        outcomes[record.path] = f"{len(chunks)} chunks, {len(tags)} tags"
    return outcomes


def main(argv: list[str] | None = None) -> int:
    outcomes = rebuild_chunks()
    for path, outcome in outcomes.items():
        print(f"{path}: {outcome}")
    if not outcomes:
        print("the bundle has no ingested originals")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
