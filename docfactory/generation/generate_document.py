"""Generate one document of one application from its YAML template (CLAUDE.md, Phase 4: "Flow per <App> <DocType>").

1. build the body from the template and the facts and save it (`<App>.Outputs.<DocType>`);
2. derive the document control, append a revision entry when the body changed, save both;
3. find the gaps and save the needs list (`.MissingInfo`), reusing the needs choice (stored, writer, or one need per gap);
4. render `output/<App>/<DocType>.md` and `<DocType>.missing.md` (removed when there is no gap).
Control, history, needs and file writing are the shared functions of generation/.
"""
from docfactory import clock
from docfactory.generation import document_store
from docfactory.generation.build_body import build_body
from docfactory.generation.template_gaps import template_gaps
from docfactory.generation.revision_sources import changed_section_ids, template_sources
from docfactory.generation.render_document import render_document_markdown, render_document_needs
from docfactory.generation.template_loader import load_template
from docfactory.documentmodels.document_control import DocumentControl
from docfactory.documentmodels.missing_info import MissingInfo
from docfactory.documentmodels.revision_history import RevisionHistory
from docfactory.documentsaver.document_body_saver import DocumentBodySaver
from docfactory.documentsaver.document_control_saver import DocumentControlSaver
from docfactory.documentsaver.missing_info_saver import MissingInfoSaver
from docfactory.documentsaver.revision_history_saver import RevisionHistorySaver
from docfactory.generation.document_control import document_version, next_control
from docfactory.generation.gaps import gaps_hash
from docfactory.generation.generation_steps import NeedsWriter, choose_needs, output_dir, save_object, write_if_changed
from docfactory.generation.revision_history import RECOVERED, history_is_behind, next_history, revision_summary
from docfactory.models.generation_report import GenerationReport
from docfactory.models.save_action import SaveAction


def generate_document(app_id: str, doc_type: str, writer: NeedsWriter | None = None) -> GenerationReport:
    """Generate `app_id`'s `doc_type` document from its template; `writer` phrases the needs list (None = one need per gap)."""
    template = load_template(doc_type)
    prefix, today = document_store.prefix(app_id, doc_type), clock.now_iso()[:10]
    errors: list[str] = []

    old_body = document_store.stored_row(prefix)
    body = build_body(template, app_id)
    body_result = save_object(DocumentBodySaver(), prefix, body, errors)
    report = GenerationReport(doc_type=doc_type, body_key=prefix, body_action=body_result.action,
                              body_version=body_result.version, body_completeness=body_result.completeness)
    if not body_result.ok:
        return report.model_copy(update={"errors": errors})

    stored_control = document_store.stored_model(DocumentControl, f"{prefix}.DocumentControl")
    stored_history = document_store.stored_model(RevisionHistory, f"{prefix}.RevisionHistory")
    body_changed = body_result.action in (SaveAction.CREATED, SaveAction.UPDATED)
    first = old_body is None or stored_history is None
    version = document_version(body_result.version)
    sections = changed_section_ids(None if first else old_body["Value"], body)
    behind = history_is_behind(stored_history, version)  # an earlier run saved this body but stopped before its history
    summary = revision_summary(True, sections, template_sources(template, app_id)) if first else         revision_summary(False, sections, template_sources(template, app_id)) if body_changed else RECOVERED
    history, entry = next_history(stored_history, body_changed or behind, version, summary, today)
    control = next_control(app_id, doc_type, template.name, stored_control, body_changed or behind, body_result.version, today)
    save_object(DocumentControlSaver(), f"{prefix}.DocumentControl", control, errors)
    save_object(RevisionHistorySaver(), f"{prefix}.RevisionHistory", history, errors)

    gaps = template_gaps(template, app_id)
    stored_needs = document_store.stored_model(MissingInfo, f"{prefix}.MissingInfo")
    needs, origin, skipped, note = choose_needs(app_id, template.name, gaps, stored_needs, writer)
    save_object(MissingInfoSaver(), f"{prefix}.MissingInfo",
                MissingInfo(gaps=gaps, needs=needs, gaps_hash=gaps_hash(gaps), needs_origin=origin), errors)

    written: list[str] = []
    if not errors:
        folder = output_dir() / app_id
        write_if_changed(folder / f"{doc_type}.md", render_document_markdown(app_id, doc_type), written)
        write_if_changed(folder / f"{doc_type}.missing.md", render_document_needs(app_id, doc_type), written)
    return report.model_copy(update={
        "document_version": control.document_version, "revision_added": entry.summary if entry else "",
        "gap_count": len(gaps), "need_count": len(needs), "needs_origin": origin.value, "needs_skipped": skipped,
        "needs_note": note, "output_files": written, "errors": errors,
    })
