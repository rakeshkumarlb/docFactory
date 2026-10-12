"""The ingestion pipeline (Phase 2): incoming/ -> staging/ -> chunk -> tag -> scope -> the bundle, all deterministic.

Per file:
1. Stage: incoming/<name> moves to staging/ (a file already waiting there under that name is replaced by the newer one).
2. Lookup by hash and by file name across all Source concepts of the bundle:
   - same name and hash stored, and the stored original is on disk with that hash: SAME, the staged copy is discarded;
   - same name and hash stored but the original is missing or different on disk: REPAIRED (put back, Source rewritten);
   - same content stored under another name: left in staging as a duplicate for a human;
   - same name stored in exactly one scope with another hash: CHANGED (scope inherited); in several scopes: left in staging;
   - otherwise NEW.
3. Chunk the original (ingest/chunking.py); no extractable text leaves it in staging.
4. Tag the chunks against the ontology (ingest/tagging.py). With a fallback, the chunks the rules left unmapped go to one LLM
   call; its tags are validated like any other and kept with origin 'llm/<model>'. Chunks still unmapped are reported.
5. Scope (NEW only, ingest/scope_rules.py). With a fallback, an unconfident scope goes to one LLM call; 'not sure' (or no
   fallback) leaves the file in staging with the reason.
6. Move staging -> <scope>/references/<name> in the bundle, then write its Source concept (<scope>/sources/<name>.md: hash, version,
   chunk outline and entity tags; no chunk text). The Source is written last, so it marks a complete ingestion. If that write fails
   the file goes back to staging (and a replaced original is restored). The resource of an original is its bundle path.
A file that stops anywhere stays in staging/ and is tried again on the next run. Nothing is ever deleted except a SAME duplicate.
"""
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from docfactory.bundle.paths import bundle_root, reference_path
from docfactory.bundle.source_store import SourceStore
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_properties import file_author
from docfactory.ingest.file_hash import file_sha256
from docfactory.ingest.paths import incoming_dir, resolve_within, staging_dir
from docfactory.ingest.scope_rules import decide_scope
from docfactory.ingest.tagging import check_tags, entity_map, is_history, tag_chunks
from docfactory.ingest.target_rules import check_target
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.ingest_outcome import IngestOutcome
from docfactory.models.ingest_report import IngestReport
from docfactory.models.source_record import SourceRecord
from docfactory.ontology.signals import entity_names, load_signals


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _files(folder: Path) -> list[Path]:
    """The files in `folder`, by name ignoring case, so the processing order (which of two duplicates wins) is the same on every OS."""
    if not folder.is_dir():
        return []
    return sorted((p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")), key=lambda p: (p.name.lower(), p.name))


def stage_incoming() -> list[str]:
    """Move every file from incoming/ to staging/; returns the names moved."""
    staging = staging_dir()
    staging.mkdir(parents=True, exist_ok=True)
    moved = []
    for path in _files(incoming_dir()):
        os.replace(path, staging / path.name)
        moved.append(path.name)
    return moved


def existing_scopes() -> list[str]:
    """The scope folders already in use: the folders of the bundle (applications, Shared, general)."""
    root = bundle_root()
    return sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")) if root.is_dir() else []


def _staged(name: str, reason: str, chunks: list[DocChunk] | None = None, tags: list[ChunkTag] | None = None,
            unmapped: list[int] | None = None) -> IngestReport:
    return IngestReport(file_name=name, outcome=IngestOutcome.STAGED, reason=reason, chunk_count=len(chunks or []),
                        entity_summary=_summary(tags or []), unmapped_chunks=unmapped or [])


def _summary(tags: list[ChunkTag]) -> list[str]:
    llm = {}
    for tag in tags:
        if tag.origin != "rule":
            llm[tag.entity] = llm.get(tag.entity, 0) + 1
    return [f"{entity}: {len(numbers)} chunks" + (f" ({llm[entity]} by {_llm_origin(tags)})" if entity in llm else "")
            for entity, numbers in entity_map(tags).items()]


def _llm_origin(tags: list[ChunkTag]) -> str:
    return next((tag.origin for tag in tags if tag.origin != "rule"), "llm")


def _matching_folder(scope: str, existing: list[str]) -> str:
    """An existing folder spelled differently (case, punctuation) is reused instead of creating a near-duplicate."""
    key = re.sub(r"[^a-z0-9]", "", scope.lower())
    return next((folder for folder in existing if re.sub(r"[^a-z0-9]", "", folder.lower()) == key), scope)


def _lookup(name: str, hashcode: str) -> tuple[IngestOutcome | None, str | None, str]:
    """(outcome so far, target path, reason). Outcome SAME / STAGED end the file here; None means NEW."""
    sources = SourceStore()
    same_hash = sources.find(hashcode=hashcode)
    named = [record for record in same_hash if record.path.rsplit("/", 1)[-1] == name]
    if named:
        record = named[0]
        stored = sources.original(record.path)
        if stored.is_file() and file_sha256(stored) == hashcode:
            return IngestOutcome.SAME, record.path, "identical file already stored"
        return IngestOutcome.REPAIRED, record.path, "stored Source found but the original was missing or altered on disk"
    if same_hash:
        paths = ", ".join(record.path for record in same_hash)
        return IngestOutcome.STAGED, None, f"same content already stored as {paths}: a duplicate under another name"
    same_name = sources.find(file_name=name)
    if len(same_name) > 1:
        paths = ", ".join(record.path for record in same_name)
        return IngestOutcome.STAGED, None, f"a file with this name is stored in several scopes ({paths}): decide which one this replaces"
    if same_name:
        return IngestOutcome.CHANGED, same_name[0].path, f"new revision of {same_name[0].path}"
    return None, None, ""


def _changed_entities(before: SourceRecord | None, chunks: list[DocChunk], tags: list[ChunkTag]) -> list[str]:
    """Entities to re-extract after a CHANGED file: tagged on a chunk whose text is new, or were tagged on a chunk that is gone."""
    if before is None:
        return []
    old_hashes = {chunk.text_hash for chunk in before.chunks}
    new_hashes = {chunk.text_hash for chunk in chunks}
    new_chunks = {chunk.chunk_no for chunk in chunks if chunk.text_hash not in old_hashes}
    gone_chunks = {chunk.chunk_no for chunk in before.chunks if chunk.text_hash not in new_hashes}
    entities = {tag.entity for tag in tags if tag.chunk_no in new_chunks}
    entities |= {tag.entity for tag in before.tags if tag.chunk_no in gone_chunks}
    return sorted(entities)


def _store(staged: Path, target: str, hashcode: str, timestamp: str, chunks: list[DocChunk], tags: list[ChunkTag]) -> tuple[int, SourceRecord | None]:
    """Move the staged file into place and write its Source; undo the move if the Source write fails."""
    destination = resolve_within(bundle_root(), target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(destination.name + ".replacing") if destination.exists() else None
    if backup is not None:
        os.replace(destination, backup)
    shutil.move(str(staged), str(destination))
    try:
        result = SourceStore().write(target, hashcode, timestamp, chunks, tags, file_author(destination))
    except Exception:
        shutil.move(str(destination), str(staged))
        if backup is not None:
            os.replace(backup, destination)
        raise
    if backup is not None:
        backup.unlink()
    return result


def ingest_staged(name: str, clock: Callable[[], str] = _now, fallback=None) -> IngestReport:
    """Ingest one file waiting in staging/ (steps 2-6 of the module docstring). `fallback` is an IngestionFallback (or None: rules only)."""
    staged = staging_dir() / name
    hashcode = file_sha256(staged)
    outcome, target, reason = _lookup(name, hashcode)
    if outcome == IngestOutcome.STAGED:
        return _staged(name, reason)
    if outcome == IngestOutcome.SAME:
        staged.unlink()
        record = SourceStore().read(target)
        return IngestReport(file_name=name, outcome=outcome, target_path=target, version=record.version, reason=reason,
                            chunk_count=len(record.chunks))
    try:
        chunks = chunk_file(staged)
    except Exception as error:  # unsupported type or a file the reader cannot parse: a human looks at it
        return _staged(name, f"could not chunk: {error}")
    if not chunks:
        return _staged(name, "no extractable text (a scanned PDF needs OCR, which is not supported)")
    tags, unmapped = tag_chunks(chunks, load_signals())
    notes = []
    if fallback is not None and any(c.chunk_no in unmapped and not is_history(c) for c in chunks):
        llm_tags, note = fallback.tag_chunks([chunk for chunk in chunks if chunk.chunk_no in unmapped and not is_history(chunk)])
        rejected = check_tags(llm_tags, chunks, entity_names())
        if rejected:
            llm_tags, note = [], "LLM tags rejected: " + "; ".join(rejected)
        tags += llm_tags
        tagged = {tag.chunk_no for tag in llm_tags}
        unmapped = [no for no in unmapped if no not in tagged]
        if note:
            notes.append(note)
    problems = check_tags(tags, chunks, entity_names())
    if problems:
        return _staged(name, "invalid tags: " + "; ".join(problems), chunks, tags, unmapped)
    if outcome is None:
        existing = existing_scopes()
        scope, confident, reason = decide_scope(chunks, tags, existing)
        if (scope is None or not confident) and fallback is not None:
            llm_scope, llm_reason = fallback.decide_scope(chunks[:3], tags, existing, reason)
            if llm_scope:
                scope, confident, reason = _matching_folder(llm_scope, existing), True, f"{fallback.origin}: {llm_reason}"
            else:
                reason = f"{reason}; {fallback.origin}: {llm_reason}"
        if scope is None or not confident:
            return _staged(name, "; ".join([f"scope unsure ({reason})", *notes]), chunks, tags, unmapped)
        problem = check_target(name, f"{scope}/{name}")
        if problem:
            return _staged(name, problem, chunks, tags, unmapped)
        target = reference_path(scope, name)
        outcome = IngestOutcome.NEW
    version, before = _store(staged, target, hashcode, clock(), chunks, tags)
    changed = _changed_entities(before, chunks, tags) if outcome == IngestOutcome.CHANGED else []
    return IngestReport(file_name=name, outcome=outcome, target_path=target, version=version, chunk_count=len(chunks),
                        entity_summary=_summary(tags), unmapped_chunks=unmapped, changed_entities=changed,
                        reason="; ".join(part for part in [reason, *notes] if part))


def run_ingest(clock: Callable[[], str] = _now, fallback=None) -> list[IngestReport]:
    """Stage everything in incoming/, then ingest every file in staging/ (including ones left there by earlier runs)."""
    stage_incoming()
    return [ingest_staged(path.name, clock, fallback) for path in _files(staging_dir())]


def format_reports(reports: list[IngestReport]) -> str:
    """The plain-text run report: one block per file."""
    if not reports:
        return "nothing to ingest: incoming/ and staging/ are empty"
    lines = []
    for report in reports:
        where = f" -> {report.target_path} (v{report.version})" if report.target_path else ""
        lines.append(f"{report.file_name}: {report.outcome.value}{where}")
        if report.reason:
            lines.append(f"  reason: {report.reason}")
        if report.chunk_count:
            lines.append(f"  chunks: {report.chunk_count}")
        lines += [f"  {line}" for line in report.entity_summary]
        if report.unmapped_chunks:
            lines.append(f"  unmapped chunks: {', '.join(map(str, report.unmapped_chunks))}")
        if report.changed_entities:
            lines.append(f"  changed entities (re-extract): {', '.join(report.changed_entities)}")
    return "\n".join(lines)
