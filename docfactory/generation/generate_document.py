"""Generate one document of one application (CLAUDE.md, Phase 4: "Flow per <App> <DocType>"). Code does all of it except phrasing the needs.

1. build the body from the bound facts (build_document) and save it (`<App>.Outputs.<DocType>`);
2. derive the document control and append a revision entry when the body changed, and save both;
3. find the gaps, and save the needs list (`.MissingInfo`): the stored needs when the gaps did not change, else the needs writer's
   answer, else one need per gap (no writer, or the writer failed);
4. render `output/<App>/<DocType>.md` and `<DocType>.missing.md` (removed when there is no gap).
An absent or incomplete fact never stops it: its fields render as not provided and reach the needs list.
"""
import json
import os
from collections.abc import Callable
from pathlib import Path

from docfactory import clock, db
from docfactory.build import build_document
from docfactory.documentmodels.shared.document_control import DocumentControl
from docfactory.documentmodels.shared.document_gap import DocumentGap
from docfactory.documentmodels.shared.document_need import DocumentNeed
from docfactory.documentmodels.shared.missing_info import MissingInfo
from docfactory.documentmodels.shared.needs_origin import NeedsOrigin
from docfactory.documentmodels.shared.revision_history import RevisionHistory
from docfactory.documents import get_document
from docfactory.documentsaver.shared.document_control_saver import DocumentControlSaver
from docfactory.documentsaver.shared.missing_info_saver import MissingInfoSaver
from docfactory.documentsaver.shared.revision_history_saver import RevisionHistorySaver
from docfactory.generation.doc_types import DOC_TYPES
from docfactory.generation.document_control import document_version, next_control
from docfactory.generation.fallback_needs import fallback_needs
from docfactory.generation.gaps import document_gaps, gaps_hash
from docfactory.generation.revision_history import changed_sections, next_history, revision_summary, section_sources
from docfactory.models.generation_report import GenerationReport
from docfactory.models.save_action import SaveAction
from docfactory.render import render_markdown, render_needs_markdown

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


def stored_object(model, key: str, table: str = "DocumentOutputs"):
    row = db.get_row(table, key)
    return model.model_validate(json.loads(row["Value"])) if row else None


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


def generate(app_id: str, doc_type: str, writer: NeedsWriter | None = None) -> GenerationReport:
    """Generate `app_id`'s `doc_type` document; `writer` phrases the needs list (None = one need per gap, as with --no-llm)."""
    spec = DOC_TYPES[doc_type]
    model, prefix, today = spec["model"], f"{app_id}.Outputs.{doc_type}", clock.now_iso()[:10]
    errors: list[str] = []

    old_body = get_document(prefix)
    body, _ = build_document(model, app_id)
    body_result = save_object(spec["saver"](), prefix, body, errors)
    report = GenerationReport(doc_type=doc_type, body_key=prefix, body_action=body_result.action,
                              body_version=body_result.version, body_completeness=body_result.completeness)
    if not body_result.ok:
        return report.model_copy(update={"errors": errors})

    stored_control = stored_object(DocumentControl, f"{prefix}.DocumentControl")
    stored_history = stored_object(RevisionHistory, f"{prefix}.RevisionHistory")
    body_changed = body_result.action in (SaveAction.CREATED, SaveAction.UPDATED)
    first = old_body is None or stored_history is None
    version = document_version(body_result.version)
    summary = revision_summary(first, changed_sections(None if first else old_body.value, body), section_sources(model, app_id))
    history, entry = next_history(stored_history, body_changed, version, summary, today)
    control = next_control(app_id, doc_type, spec["name"], stored_control, body_result.action, body_result.version, today)
    save_object(DocumentControlSaver(), f"{prefix}.DocumentControl", control, errors)
    save_object(RevisionHistorySaver(), f"{prefix}.RevisionHistory", history, errors)

    gaps = document_gaps(model, app_id)
    needs, origin, skipped, note = choose_needs(app_id, spec["name"], gaps, stored_object(MissingInfo, f"{prefix}.MissingInfo"), writer)
    save_object(MissingInfoSaver(), f"{prefix}.MissingInfo", MissingInfo(gaps=gaps, needs=needs, gaps_hash=gaps_hash(gaps), needs_origin=origin), errors)

    written: list[str] = []
    if not errors:
        folder = output_dir() / app_id
        write_if_changed(folder / f"{doc_type}.md", render_markdown(app_id, doc_type), written)
        write_if_changed(folder / f"{doc_type}.missing.md", render_needs_markdown(app_id, doc_type), written)
    return report.model_copy(update={
        "document_version": control.document_version, "revision_added": entry.summary if entry else "",
        "gap_count": len(gaps), "need_count": len(needs), "needs_origin": origin.value, "needs_skipped": skipped,
        "needs_note": note, "output_files": written, "errors": errors,
    })


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
