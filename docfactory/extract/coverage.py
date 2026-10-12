"""Coverage report: for every chunk of an ingested original, is its content in a fact? Deterministic, read-only, no LLM.

A chunk is EXTRACTED when an entity it is tagged with has a stored contribution from this file whose chunks hash equals the hash of
the entity's current chunks (the same test the extraction uses to skip an unchanged entity). Otherwise it is NOT_EXTRACTED when some
tagged entity could have a fact from this file (`fact_key`), SKIPPED_SCOPE when none could, and UNMAPPED when it carries no tag.
A chunk with several tags takes the best status of its entities. A chunk that would be SKIPPED_SCOPE or UNMAPPED but is named by a note of
this file's Note contribution (`<resource>#<chunk>` in a note's source_chunks) is NOTED: kept, though in no knowledge fact.
"""
import json

from docfactory.bundle.contribution_store import ContributionStore
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.batching import chunks_hash
from docfactory.extract.fact_keys import fact_key
from docfactory.ingest.source_reads import read_chunks
from docfactory.models.chunk_coverage import ChunkCoverage
from docfactory.models.coverage_report import CoverageReport
from docfactory.models.coverage_status import CoverageStatus

NO_TAG = "no entity is tagged on this chunk"
ORDER = [CoverageStatus.EXTRACTED, CoverageStatus.NOTED, CoverageStatus.NOT_EXTRACTED, CoverageStatus.SKIPPED_SCOPE, CoverageStatus.UNMAPPED]
LOST = (CoverageStatus.SKIPPED_SCOPE, CoverageStatus.UNMAPPED)  # not in any fact: the chunks discovery looks at


def _entity_states(path: str, by_entity: dict) -> dict[str, tuple[CoverageStatus, str]]:
    """(status, reason) of each tagged entity of the file: whether its current chunks are in a stored contribution."""
    states = {}
    for entity, chunks in by_entity.items():
        key, why = fact_key(path, entity)
        if key is None:
            states[entity] = (CoverageStatus.SKIPPED_SCOPE, why)
            continue
        stored = ContributionStore().get(key, path)
        if stored is None:
            states[entity] = (CoverageStatus.NOT_EXTRACTED, f"{entity} is not extracted from this file yet")
        elif stored.chunks_hash is None:
            states[entity] = (CoverageStatus.NOT_EXTRACTED, f"{entity}: a batch failed in the last extraction; the next run tries again")
        elif stored.chunks_hash != chunks_hash(chunks):
            states[entity] = (CoverageStatus.NOT_EXTRACTED, f"{entity}: the chunks changed since the last extraction")
        else:
            states[entity] = (CoverageStatus.EXTRACTED, "")
    return states


def noted_chunks(path: str) -> set[int]:
    """The numbers of the chunks of the original `path` that a note of its stored Note contribution names."""
    key, _ = fact_key(path, "Note")
    stored = ContributionStore().get(key, path) if key else None
    if stored is None:
        return set()
    prefix = path + "#"
    return {int(ref[len(prefix):]) for note in json.loads(stored.value_json).get("notes", []) for ref in note.get("source_chunks", [])
            if ref.startswith(prefix) and ref[len(prefix):].isdigit()}


def file_coverage(path: str) -> CoverageReport:
    """The coverage of the ingested original `path` (its bundle path). Raises FileNotFoundError / ChunksOutOfDateError like `read_chunks`."""
    path = path.replace("\\", "/").strip("/")
    record, chunks = read_chunks(path)
    by_number = {chunk.chunk_no: chunk for chunk in chunks}
    tagged: dict[int, set[str]] = {}
    by_entity: dict[str, list] = {}
    for tag in record.tags:
        tagged.setdefault(tag.chunk_no, set()).add(tag.entity)
        by_entity.setdefault(tag.entity, []).append(by_number[tag.chunk_no])
    states = _entity_states(path, by_entity)
    noted = noted_chunks(path)
    rows = []
    for chunk in chunks:
        entities = sorted(tagged.get(chunk.chunk_no, ()))
        if not entities:
            status, reason = CoverageStatus.UNMAPPED, NO_TAG
        else:
            status = min((states[e][0] for e in entities), key=ORDER.index)
            reason = "; ".join(sorted({states[e][1] for e in entities if states[e][0] == status and states[e][1]}))
        if status in LOST and chunk.chunk_no in noted:
            status, reason = CoverageStatus.NOTED, "kept as a note"
        rows.append(ChunkCoverage(chunk_no=chunk.chunk_no, heading=chunk.heading, chars=len(chunk.text), status=status, entities=entities, reason=reason))
    return CoverageReport(path=path, chunks=rows)


def all_coverage() -> list[CoverageReport]:
    """The coverage of every ingested original of the bundle, ordered by path."""
    return [file_coverage(record.path) for record in SourceStore().list()]


def format_coverage(reports: list[CoverageReport]) -> str:
    """The plain-text report: per file a summary by status (chunks and characters), then every chunk whose content is not in a fact."""
    if not reports:
        return "no ingested originals in the bundle"
    lines = []
    for report in reports:
        total_chars = sum(c.chars for c in report.chunks) or 1
        lines.append(f"{report.path}: {len(report.chunks)} chunks")
        for status in ORDER:
            rows = [c for c in report.chunks if c.status == status]
            chars = sum(c.chars for c in rows)
            lines.append(f"  {status.value:<14} {len(rows):>4} chunks {chars:>8} chars {100 * chars / total_chars:5.1f}%")
        for status in ORDER[1:]:
            for c in (c for c in report.chunks if c.status == status):
                tags = f" [{', '.join(c.entities)}]" if c.entities else ""
                lines.append(f"    {status.value} chunk {c.chunk_no} ({c.chars} chars) {c.heading}{tags}: {c.reason}")
    return "\n".join(lines)
