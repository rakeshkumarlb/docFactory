"""Recognize the entities and relationships of one ingested original and rebuild its scope's entity graph. Code orchestrates; the LLM only
answers per window.

Per original (its chunks re-derived from the file):
1. the chunks are cut into windows of whole sections (`windows.build_windows`, word-capped);
2. a window whose chunks are covered by stored window recognitions with matching hashes is reused without an LLM call (unless `force`);
3. every other window is one fresh single-tool call (`EntityRecognizer`) that sees the document's outline, the window, the type vocabulary,
   the part of the entity graph the window may refer to (including what earlier windows of this file found) and the keyword-rule hints;
   a failed window of several chunks is split in half and retried; a failed single chunk is reported and retried on the next run;
4. the accepted windows are stored as the file's recognition (`RecognitionStore`), replacing its earlier one;
5. the scope's entity graph is re-merged from all its recognitions, oldest original first (`entity_merge`), and written (`EntityStore`).
"""
from docfactory import clock
from docfactory.agents.entity_recognizer import EntityRecognizer
from docfactory.bundle.entity_store import EntityStore
from docfactory.bundle.recognition_store import RecognitionStore
from docfactory.bundle.resolution_store import ResolutionStore
from docfactory.bundle.source_store import SourceStore
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.extract.batching import batch_text
from docfactory.ingest.source_reads import read_chunks
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.entity_record import EntityRecord
from docfactory.models.file_recognition import FileRecognition
from docfactory.models.recognition_outcome import RecognitionOutcome
from docfactory.models.recognition_report import RecognitionReport
from docfactory.models.source_record import SourceRecord
from docfactory.models.window_recognition import WindowRecognition
from docfactory.recognize.catalog_filter import catalog_for
from docfactory.recognize.entity_merge import merge_entities
from docfactory.recognize.type_vocabulary import types_of_fact
from docfactory.recognize.windows import build_windows, outline_text, window_hash


def _file_recognition(resource: str, windows: list[WindowRecognition], actor: str) -> FileRecognition:
    data = [w.model_dump(mode="json") for w in windows]
    return FileRecognition(resource=resource, windows=windows, hashcode=sha256_hex(canonical_json(data)), generated_by=actor, timestamp=clock.now_iso())


def _sources(scope: str) -> list[SourceRecord]:
    """The Sources of a scope, oldest ingested first (then by path): the order in which recognitions are merged."""
    return sorted(SourceStore().list(scope), key=lambda r: (r.timestamp, r.path))


def scope_graph(scope: str, replace: FileRecognition | None = None, resolved: bool = True) -> tuple[list[EntityRecord], list[str]]:
    """(the entity graph of `scope`, merge notes) from its stored recognitions, with `replace` standing in for the stored recognition of its
    resource, and the scope's entity resolution decisions applied unless `resolved` is False."""
    sources = _sources(scope)
    stored = {r.resource: r for r in RecognitionStore().list(scope)}
    if replace is not None:
        stored[replace.resource] = replace
    order = {s.path: i for i, s in enumerate(sources)}
    recognitions = sorted(stored.values(), key=lambda r: (order.get(r.resource, len(order)), r.resource))
    outlines = {s.path: {c.chunk_no: c for c in s.chunks} for s in sources}
    decisions = ResolutionStore().get(scope) if resolved else None
    return merge_entities(scope, recognitions, outlines, decisions.groups if decisions else None)


def rebuild_graph(scope: str) -> tuple[dict[str, list[str]], list[str]]:
    """Re-merge the entity graph of `scope` from its recognitions and write it; returns (created/updated/removed ids, merge notes)."""
    records, notes = scope_graph(scope)
    return EntityStore().write_all(scope, records, clock.now_iso()), notes


def _reusable(window: list[DocChunk], stored: list[WindowRecognition]) -> list[WindowRecognition] | None:
    """Stored window recognitions that exactly cover `window` and whose chunks are unchanged, in order; None when they do not."""
    by_no = {c.chunk_no: c for c in window}
    found = [w for w in stored if w.chunk_nos and set(w.chunk_nos) <= set(by_no)
             and w.window_hash == window_hash([by_no[n] for n in w.chunk_nos])]
    covered = sorted(n for w in found for n in w.chunk_nos)
    return sorted(found, key=lambda w: w.chunk_nos[0]) if covered == sorted(by_no) else None


def _hints(window: list[DocChunk], record: SourceRecord) -> tuple[list[str], set[str]]:
    """(hint lines for the prompt, the entity types they point to) from the keyword-rule tags of the window's chunks."""
    numbers = {c.chunk_no for c in window}
    tags = [t for t in record.tags if t.chunk_no in numbers]
    lines = [f"chunk {t.chunk_no}: {t.entity}" for t in sorted(tags, key=lambda t: (t.chunk_no, t.entity))]
    return lines, {kind for t in tags for kind in types_of_fact(t.entity)}


def recognize_file(path: str, recognizer: EntityRecognizer, force: bool = False) -> RecognitionReport:
    """Recognize the ingested original `path` (its bundle path), store its recognition, rebuild its scope's entity graph and return the report.

    `force` sends every window to the model again. Raises FileNotFoundError for an original with no Source.
    """
    path = path.replace("\\", "/").strip("/")
    record, chunks = read_chunks(path)
    scope = path.split("/")[0]
    windows = build_windows(chunks)
    previous = RecognitionStore().get(path)
    stored = previous.windows if previous and not force else []
    outline = outline_text(chunks)
    accepted: list[WindowRecognition] = []
    notes: list[str] = []
    calls = skipped = failed = 0
    pending = list(windows)
    while pending:
        window = pending.pop(0)
        reused = _reusable(window, stored)
        if reused is not None:
            accepted += reused
            skipped += 1
            continue
        graph, _ = scope_graph(scope, _file_recognition(path, accepted, recognizer.actor))
        lines, hint_types = _hints(window, record)
        catalog = catalog_for(batch_text(window), graph, hint_types)
        result, note = recognizer.recognize_window(path, outline, window, catalog, lines)
        calls += 1
        label = f"chunks {window[0].chunk_no}-{window[-1].chunk_no}"
        if result is not None:
            accepted.append(result)
        elif len(window) > 1:  # often an answer too long for one reply: retry the halves, in order
            half = len(window) // 2
            pending[:0] = [window[:half], window[half:]]
            notes.append(f"{label}: {note}; split and retried in two halves")
        else:
            failed += 1
            notes.append(f"{label}: {note}")
    accepted.sort(key=lambda w: w.chunk_nos[0])
    report = {"path": path, "windows": len(windows), "calls": calls, "skipped_windows": skipped, "failed_windows": failed,
              "entities": sum(len(w.entities) for w in accepted), "relations": sum(len(w.relations) for w in accepted)}
    if not accepted:
        return RecognitionReport(outcome=RecognitionOutcome.FAILED, notes=notes, **report)
    RecognitionStore().save(path, accepted, recognizer.actor if calls else (previous.generated_by if previous else recognizer.actor),
                            clock.now_iso() if calls or previous is None else previous.timestamp)
    done, merge_notes = rebuild_graph(scope)
    notes += [note.removeprefix(f"{path}: ") for note in merge_notes if note.startswith(f"{path}: ")]  # this file's only
    notes += [f"entities {action}: {len(ids)}" for action, ids in done.items() if ids]
    outcome = RecognitionOutcome.PARTIAL if failed else (RecognitionOutcome.RECOGNIZED if calls else RecognitionOutcome.UNCHANGED)
    return RecognitionReport(outcome=outcome, notes=notes, **report)


def format_report(report: RecognitionReport) -> str:
    """The plain-text report of one recognition run."""
    lines = [f"{report.path}: {report.outcome.value}",
             f"  windows {report.windows}, calls {report.calls}, skipped {report.skipped_windows}, failed {report.failed_windows}",
             f"  entities {report.entities}, relationships {report.relations}"]
    return "\n".join(lines + [f"  {note}" for note in report.notes])
