"""The steps every document generation shares (CLAUDE.md, Phase 4: "Flow per <App> <DocType>"), whatever defines the document.

`save_object` saves one row through its saver, `choose_needs` decides where the needs list comes from (the stored list when the gaps did
not change, else the needs writer's answer, else one need per gap), `write_if_changed` writes a rendered file only when its bytes
changed, `output_dir` says where files go and `format_reports` prints the run. The flow itself is in generation/generate_document.py.
"""
import os
from collections.abc import Callable
from pathlib import Path

from docfactory import db
from docfactory.documentmodels.document_gap import DocumentGap
from docfactory.documentmodels.document_need import DocumentNeed
from docfactory.documentmodels.missing_info import MissingInfo
from docfactory.documentmodels.needs_origin import NeedsOrigin
from docfactory.generation.fallback_needs import fallback_needs
from docfactory.generation.gaps import gaps_hash
from docfactory.models.generation_report import GenerationReport

ENV_VAR = "DOCFACTORY_OUTPUT"

# (application, document name, numbered gaps) -> (the needs, '') or (None, what went wrong)
NeedsWriter = Callable[[str, str, list[DocumentGap]], tuple[list[DocumentNeed] | None, str]]


def output_dir() -> Path:
    """Where rendered documents go: env DOCFACTORY_OUTPUT, else output/ in the project."""
    override = os.environ.get(ENV_VAR)
    return Path(override) if override else db.PROJECT_ROOT / "output"


def _shown(path: Path) -> str:
    try:
        return path.resolve().relative_to(db.PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def save_object(saver, key: str, value, errors: list[str]):
    result = saver.save(key, value.model_dump(mode="json"))
    if not result.ok:
        errors.append(f"{key}: {result.action.value}: " + "; ".join(f"{e.path}: {e.message}" for e in result.errors))
    return result


def choose_needs(app_id: str, doc_name: str, gaps: list[DocumentGap], stored: MissingInfo | None, writer: NeedsWriter | None):
    """(needs, origin, skipped, note) for these gaps."""
    target = NeedsOrigin.LLM if writer is not None and gaps else NeedsOrigin.NO_LLM
    if stored is not None and stored.gaps_hash == gaps_hash(gaps) and stored.needs_origin in (NeedsOrigin.LLM, target):
        return stored.needs, stored.needs_origin, True, ""
    if target is NeedsOrigin.NO_LLM:
        return fallback_needs(gaps), NeedsOrigin.NO_LLM, False, ""
    needs, note = writer(app_id, doc_name, gaps)
    if needs is None:
        return fallback_needs(gaps), NeedsOrigin.FALLBACK, False, note
    return needs, NeedsOrigin.LLM, False, ""


def write_if_changed(path: Path, text: str | None, written: list[str]) -> None:
    if text is None:
        if path.exists():
            path.unlink()
            written.append(f"removed {_shown(path)}")
        return
    data = text.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return  # same rows, same bytes: nothing to write
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    written.append(_shown(path))


def format_reports(app_id: str, reports: list[GenerationReport]) -> str:
    """The plain-text run report: one block per document."""
    lines = [app_id]
    for r in reports:
        body = f"{r.body_action.value} v{r.body_version}, {r.body_completeness:.0f}% complete" if r.body_version is not None else str(r.body_action)
        lines.append(f"  {r.doc_type}: body {body}; document version {r.document_version or '-'}")
        if r.revision_added:
            lines.append(f"    revision added: {r.revision_added}")
        origin = f"{r.needs_origin}" + (", unchanged gaps, no LLM call" if r.needs_skipped else "")
        lines.append(f"    needs list: {r.gap_count} gaps, {r.need_count} needs ({origin})")
        if r.needs_note:
            lines.append(f"    needs fallback: {r.needs_note}")
        lines += [f"    wrote {path}" for path in r.output_files]
        lines += [f"    error: {error}" for error in r.errors]
    return "\n".join(lines)
