"""Tag the stored originals with one entity that was added to the ontology later: `python -m docfactory.ingest.retag_entity <Entity>`.

Unlike `chunk_rebuild` this keeps every existing tag (including the LLM-fallback tags, which cost a call) and only adds the tags the signals of the
named entity give by the deterministic rules. A Source whose original is missing, or that no longer chunks as stored, is reported and left alone.
"""
import sys

from docfactory.bundle.source_store import SourceStore
from docfactory.ingest.source_reads import read_chunks
from docfactory.ingest.tagging import tag_chunk
from docfactory.ontology.signals import load_signals


def retag_entity(entity: str) -> dict[str, str]:
    """Path -> outcome ('N new tags' or why the file was left alone). ValueError when `entity` has no signals."""
    signals = [entry for entry in load_signals() if entry.entity == entity]
    if not signals:
        raise ValueError(f"{entity!r} has no tagging signals; add it to docfactory/ontology/signals.json")
    store = SourceStore()
    outcomes = {}
    for record in store.list():
        try:
            record, chunks = read_chunks(record.path)
        except Exception as error:  # a file that cannot be read is reported, never fatal
            outcomes[record.path] = f"left alone: {error}"
            continue
        have = {(t.chunk_no, t.entity) for t in record.tags}
        added = [t for chunk in chunks for t in tag_chunk(chunk, signals) if (t.chunk_no, t.entity) not in have]
        if added:
            store.write(record.path, record.hashcode, record.timestamp, chunks, sorted(record.tags + added, key=lambda t: (t.chunk_no, t.entity)))
        outcomes[record.path] = f"{len(added)} new tags"
    return outcomes


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python -m docfactory.ingest.retag_entity <Entity>")
        return 2
    try:
        outcomes = retag_entity(argv[0])
    except ValueError as error:
        print(error)
        return 1
    for path, outcome in outcomes.items():
        print(f"{path}: {outcome}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
