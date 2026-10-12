"""Discovery: keep the chunks of an ingested original that no knowledge entity claims, as notes (OKF redesign step 4).

Per file (after extraction), the chunks whose content is in no fact (UNMAPPED, SKIPPED_SCOPE, or already NOTED by an earlier run) go in batches
(`batching`), one fresh single-tool call per batch (`Discoverer`) returns notes and the chunks that hold nothing worth keeping; code checks the
answer (`discovery_tools`), merges the batches, stores them as this file's contribution to the application's Note fact and merges all contributions
through the same store path as every other fact (`extraction_pipeline.merge_and_save`). Unchanged chunks are skipped without a call; a file whose
chunks are all in facts loses its notes contribution. Notes never feed a generated document.
"""
import json

from docfactory import clock
from docfactory.agents.discoverer import Discoverer
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.contribution_store import ContributionStore
from docfactory.bundle.source_store import SourceStore
from docfactory.entitymodels.facts.note import Note
from docfactory.extract.batching import batch_chunks, chunks_hash, split_chunk
from docfactory.extract.coverage import LOST, file_coverage
from docfactory.extract.extraction_pipeline import keep_existing, merge_and_save, remove_entity
from docfactory.extract.fact_keys import fact_key
from docfactory.extract.merge import merge_partials
from docfactory.ingest.source_reads import read_chunks
from docfactory.models.coverage_status import CoverageStatus
from docfactory.models.entity_extraction_report import EntityExtractionReport
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.note_draft import NoteDraft
from docfactory.models.save_action import SaveAction

ENTITY = "Note"


def _partial(path: str, drafts: list[NoteDraft]) -> dict:
    """The notes as a partial Note value: only the fields a draft actually gives, with the chunk references `<path>#<chunk>`."""
    notes = []
    for draft in drafts:
        note = {"title": draft.title.strip(), "source_chunks": [f"{path}#{n}" for n in sorted(set(draft.chunks))]}
        for name, value in (("summary", draft.summary.strip()), ("statements", [s.strip() for s in draft.statements if s.strip()]), ("kind", draft.kind.strip())):
            if value:
                note[name] = value
        notes.append(note)
    return {"notes": notes} if notes else {}


def _has_notes(key: str) -> bool:
    return any(json.loads(c.value_json).get("notes") for c in ContributionStore().list(key))


def discover_file(path: str, discoverer: Discoverer, force: bool = False) -> EntityExtractionReport:
    """Keep the chunks of the ingested original `path` that are in no fact as notes and return the report (entity `Note`).

    `force` asks again although the chunks are unchanged. Raises FileNotFoundError for an original with no Source.
    """
    path = path.replace("\\", "/").strip("/")
    if SourceStore().read(path) is None:
        raise FileNotFoundError(f"no such file in the bundle: {path}")
    report = {"entity": ENTITY, "conflicts": [], "ungrounded_values": [], "batch_notes": [], "priorities_from_keywords": 0}
    key, why = fact_key(path, ENTITY)
    if key is None:
        return EntityExtractionReport(outcome=ExtractionOutcome.SKIPPED_SCOPE, reason=why, **report)
    report["key"] = key
    wanted = {c.chunk_no for c in file_coverage(path).chunks if c.status in LOST or c.status == CoverageStatus.NOTED}
    stored = ContributionStore().get(key, path)
    if not wanted:
        if stored is not None:
            return remove_entity(path, key, discoverer.actor).model_copy(update={"entity": ENTITY})
        return EntityExtractionReport(outcome=ExtractionOutcome.SKIPPED_UNCHANGED_CHUNKS, reason="every chunk is in a knowledge fact", **report)
    _, all_chunks = read_chunks(path)
    chunks = [c for c in all_chunks if c.chunk_no in wanted]
    report["chunks_used"] = len(chunks)
    current_hash = chunks_hash(chunks)
    if stored is not None and stored.chunks_hash == current_hash and not force:
        return EntityExtractionReport(outcome=ExtractionOutcome.SKIPPED_UNCHANGED_CHUNKS, contributions=len(ContributionStore().list(key)),
                                      reason="the chunks that are in no fact are unchanged since the last discovery", **report)
    pending = batch_chunks(chunks)
    answers, calls, failed = [], 0, 0
    while pending:
        batch = pending.pop(0)
        accepted, note = discoverer.discover_batch(path, batch)
        calls += 1
        label = f"chunks {batch[0].chunk_no}-{batch[-1].chunk_no}"
        if accepted is None:
            if len(batch) > 1:  # often an answer too long for one reply: retry the halves, in order
                half = len(batch) // 2
                pending[:0] = [batch[:half], batch[half:]]
                report["batch_notes"].append(f"{label}: {note}; split and retried in two halves")
            elif len(split_chunk(batch[0])) > 1:
                pending[:0] = [[half] for half in split_chunk(batch[0])]
                report["batch_notes"].append(f"{label}: {note}; the chunk was cut in two and retried")
            else:
                failed += 1
                report["batch_notes"].append(f"{label}: {note}")
            continue
        answers.append((label, _partial(path, accepted[0])))
    report["batches"], report["failed_batches"] = calls, failed
    if failed and not any(value for _, value in answers):
        return EntityExtractionReport(outcome=ExtractionOutcome.FAILED, reason="no batch gave an accepted answer; nothing was stored", **report)
    file_value, conflicts = merge_partials(Note, answers)
    report["conflicts"] += conflicts
    keep_existing(key)
    ContributionStore().save(key, path, file_value, None if failed else current_hash, None, discoverer.actor, clock.now_iso())
    if not _has_notes(key):
        if BundleStore().delete_fact(key, discoverer.actor):
            report["reason"] = "no passage worth keeping is left; the Note fact was removed"
        return EntityExtractionReport(outcome=ExtractionOutcome.UNCHANGED, reason=report.get("reason", "none of the chunks holds anything worth keeping"), **report)
    report["outcome"] = ExtractionOutcome.SAVED
    merge_and_save(key, Note, discoverer.actor, report)
    if report["outcome"] == ExtractionOutcome.SAVED and report.get("action") == SaveAction.UNCHANGED:
        report["outcome"] = ExtractionOutcome.UNCHANGED
    return EntityExtractionReport(**report)
