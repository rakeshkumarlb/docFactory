"""The ingestion pipeline (Phase 2): incoming/ -> staging/ -> chunk -> tag -> scope -> DocStore/, all deterministic.

Per file:
1. Stage: incoming/<name> moves to staging/ (a file already waiting there under that name is replaced by the newer one).
2. Lookup by hash and by file name across all scopes:
   - same name and hash stored, and the stored file is on disk with that hash: SAME, the staged copy is discarded;
   - same name and hash stored but the file is missing or different on disk: REPAIRED (put back, chunks rewritten);
   - same content stored under another name: left in staging as a duplicate for a human;
   - same name stored in exactly one scope with another hash: CHANGED (scope inherited); in several scopes: left in staging;
   - otherwise NEW.
3. Chunk the original (ingest/chunking.py); no extractable text leaves it in staging.
4. Tag the chunks against the ontology (ingest/tagging.py); unmapped chunks are reported.
5. Scope (NEW only, ingest/scope_rules.py); an unconfident scope leaves the file in staging with the reason.
6. Move staging -> DocStore/<scope>/<name> and, in one transaction, write DocStore / DocStoreHistory, DocChunks and DocChunkTags.
   If the database write fails the file goes back to staging (and a replaced original is restored), so files and rows agree.
A file that stops anywhere stays in staging/ and is tried again on the next run. Nothing is ever deleted except a SAME duplicate.
"""
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from docfactory import db
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.ingest.paths import docstore_dir, incoming_dir, resolve_within, staging_dir
from docfactory.ingest.scope_rules import decide_scope
from docfactory.ingest.tagging import check_tags, entity_map, tag_chunks
from docfactory.ingest.target_rules import check_target
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.ingest_outcome import IngestOutcome
from docfactory.models.ingest_report import IngestReport
from docfactory.ontology.signals import entity_names, load_signals


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")) if folder.is_dir() else []


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
    """The scope folders already in use: from the DocStore table and the DocStore folder."""
    scopes = {row["FullPath"].split("/", 1)[0] for row in db.list_docstore_rows() if "/" in row["FullPath"]}
    root = docstore_dir()
    if root.is_dir():
        scopes |= {p.name for p in root.iterdir() if p.is_dir()}
    return sorted(scopes)


def _staged(name: str, reason: str, chunks: list[DocChunk] | None = None, tags: list[ChunkTag] | None = None,
            unmapped: list[int] | None = None) -> IngestReport:
    return IngestReport(file_name=name, outcome=IngestOutcome.STAGED, reason=reason, chunk_count=len(chunks or []),
                        entity_summary=_summary(tags or []), unmapped_chunks=unmapped or [])


def _summary(tags: list[ChunkTag]) -> list[str]:
    return [f"{entity}: {len(numbers)} chunks" for entity, numbers in entity_map(tags).items()]


def _lookup(name: str, hashcode: str) -> tuple[IngestOutcome | None, str | None, str]:
    """(outcome so far, target path, reason). Outcome SAME / STAGED end the file here; None means NEW."""
    same_hash = db.find_docstore_rows(hashcode=hashcode)
    named = [row for row in same_hash if row["FullPath"].rsplit("/", 1)[-1] == name]
    if named:
        row = named[0]
        stored = docstore_dir() / row["FullPath"]
        if stored.is_file() and file_sha256(stored) == hashcode:
            return IngestOutcome.SAME, row["FullPath"], "identical file already stored"
        return IngestOutcome.REPAIRED, row["FullPath"], "stored row found but the file was missing or altered on disk"
    if same_hash:
        paths = ", ".join(row["FullPath"] for row in same_hash)
        return IngestOutcome.STAGED, None, f"same content already stored as {paths}: a duplicate under another name"
    same_name = db.find_docstore_rows(file_name=name)
    if len(same_name) > 1:
        paths = ", ".join(row["FullPath"] for row in same_name)
        return IngestOutcome.STAGED, None, f"a file with this name is stored in several scopes ({paths}): decide which one this replaces"
    if same_name:
        return IngestOutcome.CHANGED, same_name[0]["FullPath"], f"new revision of {same_name[0]['FullPath']}"
    return None, None, ""


def _changed_entities(before_chunks: list[dict], before_tags: list[dict], chunks: list[DocChunk], tags: list[ChunkTag]) -> list[str]:
    """Entities to re-extract after a CHANGED file: tagged on a chunk whose text is new, or were tagged on a chunk that is gone."""
    old_hashes = {row["TextHash"] for row in before_chunks}
    new_hashes = {chunk.text_hash for chunk in chunks}
    new_chunks = {chunk.chunk_no for chunk in chunks if chunk.text_hash not in old_hashes}
    gone_chunks = {row["ChunkNo"] for row in before_chunks if row["TextHash"] not in new_hashes}
    entities = {tag.entity for tag in tags if tag.chunk_no in new_chunks}
    entities |= {row["Entity"] for row in before_tags if row["ChunkNo"] in gone_chunks}
    return sorted(entities)


def _store(staged: Path, target: str, hashcode: str, timestamp: str, chunks: list[DocChunk], tags: list[ChunkTag]) -> tuple[str, int, list[dict]]:
    """Move the staged file into place and commit its rows; undo the move if the database write fails."""
    destination = resolve_within(docstore_dir(), target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(destination.name + ".replacing") if destination.exists() else None
    if backup is not None:
        os.replace(destination, backup)
    shutil.move(str(staged), str(destination))
    try:
        result = db.commit_ingested(
            target, hashcode, timestamp,
            [(c.chunk_no, c.heading, c.page_from, c.page_to, c.text, c.text_hash) for c in chunks],
            [(t.chunk_no, t.entity, t.origin, t.score, t.evidence) for t in tags],
        )
    except Exception:
        shutil.move(str(destination), str(staged))
        if backup is not None:
            os.replace(backup, destination)
        raise
    if backup is not None:
        backup.unlink()
    return result


def ingest_staged(name: str, clock: Callable[[], str] = _now) -> IngestReport:
    """Ingest one file waiting in staging/ (steps 2-6 of the module docstring)."""
    staged = staging_dir() / name
    hashcode = file_sha256(staged)
    outcome, target, reason = _lookup(name, hashcode)
    if outcome == IngestOutcome.STAGED:
        return _staged(name, reason)
    if outcome == IngestOutcome.SAME:
        staged.unlink()
        row = db.get_docstore_row(target)
        return IngestReport(file_name=name, outcome=outcome, target_path=target, version=row["Version"], reason=reason,
                            chunk_count=len(db.list_doc_chunks(target)))
    try:
        chunks = chunk_file(staged)
    except Exception as error:  # unsupported type or a file the reader cannot parse: a human looks at it
        return _staged(name, f"could not chunk: {error}")
    if not chunks:
        return _staged(name, "no extractable text (a scanned PDF needs OCR, which is not supported)")
    tags, unmapped = tag_chunks(chunks, load_signals())
    problems = check_tags(tags, chunks, entity_names())
    if problems:
        return _staged(name, "invalid tags: " + "; ".join(problems), chunks, tags, unmapped)
    if outcome is None:
        scope, confident, reason = decide_scope(chunks, tags, existing_scopes())
        if scope is None or not confident:
            return _staged(name, f"scope unsure ({reason})", chunks, tags, unmapped)
        target = f"{scope}/{name}"
        problem = check_target(name, target)
        if problem:
            return _staged(name, problem, chunks, tags, unmapped)
        outcome = IngestOutcome.NEW
    before_tags = db.list_doc_chunk_tags(target)
    _, version, before_chunks = _store(staged, target, hashcode, clock(), chunks, tags)
    changed = _changed_entities(before_chunks, before_tags, chunks, tags) if outcome == IngestOutcome.CHANGED else []
    return IngestReport(file_name=name, outcome=outcome, target_path=target, version=version, chunk_count=len(chunks),
                        entity_summary=_summary(tags), unmapped_chunks=unmapped, changed_entities=changed, reason=reason)


def run_ingest(clock: Callable[[], str] = _now) -> list[IngestReport]:
    """Stage everything in incoming/, then ingest every file in staging/ (including ones left there by earlier runs)."""
    stage_incoming()
    return [ingest_staged(path.name, clock) for path in _files(staging_dir())]


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
