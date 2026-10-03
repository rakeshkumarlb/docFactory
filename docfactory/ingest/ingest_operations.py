"""The deterministic operations behind the ingestion tools. No LLM, no framework; every function returns a typed model."""
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from docfactory import db
from docfactory.ingest.file_hash import file_sha256
from docfactory.ingest.paths import docstore_dir, incoming_dir, resolve_within
from docfactory.ingest.target_rules import check_target
from docfactory.ingest.text_extraction import file_text, is_text_file, sidecar_path
from docfactory.models.compare_result import CompareResult
from docfactory.models.defer_result import DeferResult
from docfactory.models.file_action import FileAction
from docfactory.models.file_info import FileInfo
from docfactory.models.store_result import StoreResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normal(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def _sidecar_rel(destination: Path) -> str | None:
    path = sidecar_path(destination)
    return path.relative_to(docstore_dir().resolve()).as_posix() if path.is_file() else None


def list_incoming() -> list[FileInfo]:
    """Every file in incoming/ (recursively), sorted by path."""
    root = incoming_dir()
    if not root.is_dir():
        return []
    files = sorted(p for p in root.rglob("*") if p.is_file())
    return [FileInfo(path=p.relative_to(root).as_posix(), size_bytes=p.stat().st_size, hashcode=file_sha256(p)) for p in files]


def read_incoming_text(path: str) -> str:
    """The text of an incoming file (markitdown for non-text). Raises ValueError for a bad path, FileNotFoundError if missing."""
    source = resolve_within(incoming_dir(), _normal(path))
    if not source.is_file():
        raise FileNotFoundError(f"no such incoming file: {path}")
    return file_text(source)


def search_docstore(folder: str | None = None, name_contains: str | None = None) -> list[dict]:
    """DocStore rows (FullPath, Hashcode, Version, Timestamp) filtered by folder and/or file-name text. Read-only."""
    return db.list_docstore_rows(folder=_normal(folder) if folder else None, name_contains=name_contains)


def compare_with_docstore(incoming_path: str, target_path: str) -> CompareResult:
    """Report NEW, SAME or CHANGED for an incoming file against a DocStore target path. Reads only, writes nothing."""
    source = resolve_within(incoming_dir(), _normal(incoming_path))
    if not source.is_file():
        raise FileNotFoundError(f"no such incoming file: {incoming_path}")
    target = _normal(target_path)
    problem = check_target(_normal(incoming_path), target)
    if problem:
        raise ValueError(problem)
    resolve_within(docstore_dir(), target)  # validates the target stays inside DocStore/
    incoming_hash = file_sha256(source)
    row = db.get_docstore_row(target)
    if row is None:
        return CompareResult(target_path=target, action=FileAction.NEW, incoming_hashcode=incoming_hash)
    action = FileAction.SAME if row["Hashcode"] == incoming_hash else FileAction.CHANGED
    return CompareResult(target_path=target, action=action, incoming_hashcode=incoming_hash,
                         stored_hashcode=row["Hashcode"], stored_version=row["Version"])


def store_file(incoming_path: str, target_path: str, clock: Callable[[], str] = _now) -> StoreResult:
    """Move an incoming file into DocStore/ at `target_path` (scope folder + file name), or replace the stored one.

    NEW/CHANGED: text is converted first (a failure changes nothing), the original is moved in, the sidecar is regenerated
    and the DocStore / DocStoreHistory rows are written. SAME: nothing is stored and the duplicate leaves incoming/.
    """
    target = _normal(target_path)
    try:
        source = resolve_within(incoming_dir(), _normal(incoming_path))
        destination = resolve_within(docstore_dir(), target)
    except ValueError as exc:
        return StoreResult(ok=False, target_path=target or "?", error=str(exc))
    if not source.is_file():
        return StoreResult(ok=False, target_path=target, error=f"no such incoming file: {incoming_path}")
    problem = check_target(_normal(incoming_path), target)
    if problem:
        return StoreResult(ok=False, target_path=target, error=problem)

    incoming_hash = file_sha256(source)
    row = db.get_docstore_row(target)
    if row is not None and row["Hashcode"] == incoming_hash:
        source.unlink()
        return StoreResult(ok=True, target_path=target, action=FileAction.SAME, version=row["Version"],
                           sidecar_path=_sidecar_rel(destination))

    text = None
    if not is_text_file(source):
        try:
            text = file_text(source)
        except Exception as exc:  # conversion libraries raise many types; report, change nothing
            return StoreResult(ok=False, target_path=target, error=f"could not convert to text: {exc}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    sidecar = None
    if text is not None:
        sidecar_path(destination).write_text(text, encoding="utf-8")
        sidecar = _sidecar_rel(destination)
    action, version = db.write_docstore_row(target, incoming_hash, clock())
    return StoreResult(ok=True, target_path=target, action=FileAction(action), version=version, sidecar_path=sidecar)


def defer_file(path: str, reason: str) -> DeferResult:
    """Leave an incoming file where it is, with a stated reason, for a human to decide."""
    if not reason or not reason.strip():
        raise ValueError("a reason is required")
    resolve_within(incoming_dir(), _normal(path))
    return DeferResult(ok=True, path=_normal(path), reason=reason.strip())
