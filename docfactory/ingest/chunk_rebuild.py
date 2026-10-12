"""Re-chunk and re-tag every stored original: `python -m docfactory.ingest.chunk_rebuild`.

Use it after the chunkers or the ontology signals change (name bundle paths on the command line to rebuild only those originals). The chunk outline and the rule tags of every Source concept are rewritten from
the originals in `<scope>/references/`; the hash and version are unchanged. LLM-fallback tags are not reproduced (ingest the file again
for those). A Source whose original is missing on disk is reported and left alone.
"""
import sys

from docfactory.bundle.source_store import SourceStore
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.tagging import tag_chunks
from docfactory.ontology.signals import load_signals


def rebuild_chunks(only: list[str] | None = None) -> dict[str, str]:
    """Path -> outcome ('N chunks, M tags', 'missing on disk' or the error). With `only` (bundle paths), just those originals are rebuilt."""
    signals = load_signals()
    store = SourceStore()
    outcomes = {}
    for record in store.list():
        if only and record.path not in only:
            continue
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
    outcomes = rebuild_chunks([a.replace("\\", "/").strip("/") for a in (argv if argv is not None else sys.argv[1:])] or None)
    for path, outcome in outcomes.items():
        print(f"{path}: {outcome}")
    if not outcomes:
        print("the bundle has no ingested originals")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
