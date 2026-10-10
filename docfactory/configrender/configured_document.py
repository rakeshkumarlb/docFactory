"""Generate one configuration-based document of one application: the same flow as generation/generate_document.py, driven by a YAML template.

1. build the body from the template and the facts and save it (`<App>.Configured.<DocType>`);
2. derive the document control, append a revision entry when the body changed, save both;
3. find the gaps and save the needs list (`.MissingInfo`), reusing the needs choice (stored, writer, or one need per gap);
4. render `output/configured/<App>/<DocType>.md` and `<DocType>.missing.md` (removed when there is no gap).
Control, history, needs and file writing are the Phase 4 functions, unchanged.
"""
from docfactory import clock
from docfactory.configrender import configured_store
from docfactory.configrender.build_configured import build_body
from docfactory.configrender.configured_gaps import configured_gaps
from docfactory.configrender.configured_revision import changed_section_ids, configured_sources
from docfactory.configrender.render_configured import render_configured_markdown, render_configured_needs
from docfactory.configrender.savers.configured_body_saver import ConfiguredBodySaver
from docfactory.configrender.savers.configured_document_control_saver import ConfiguredDocumentControlSaver
from docfactory.configrender.savers.configured_missing_info_saver import ConfiguredMissingInfoSaver
from docfactory.configrender.savers.configured_revision_history_saver import ConfiguredRevisionHistorySaver
from docfactory.configrender.template_loader import load_template
from docfactory.documentmodels.shared.document_control import DocumentControl
from docfactory.documentmodels.shared.missing_info import MissingInfo
from docfactory.documentmodels.shared.revision_history import RevisionHistory
from docfactory.generation.document_control import document_version, next_control
from docfactory.generation.gaps import gaps_hash
from docfactory.generation.generate_document import NeedsWriter, choose_needs, output_dir, save_object, write_if_changed
from docfactory.generation.revision_history import next_history, revision_summary
from docfactory.models.generation_report import GenerationReport
from docfactory.models.save_action import SaveAction


def generate_configured(app_id: str, doc_type: str, writer: NeedsWriter | None = None) -> GenerationReport:
    """Generate `app_id`'s `doc_type` document from its template; `writer` phrases the needs list (None = one need per gap)."""
    template = load_template(doc_type)
    prefix, today = configured_store.prefix(app_id, doc_type), clock.now_iso()[:10]
    errors: list[str] = []

    old_body = configured_store.stored_row(prefix)
    body = build_body(template, app_id)
    body_result = save_object(ConfiguredBodySaver(), prefix, body, errors)
    report = GenerationReport(doc_type=doc_type, body_key=prefix, body_action=body_result.action,
                              body_version=body_result.version, body_completeness=body_result.completeness)
    if not body_result.ok:
        return report.model_copy(update={"errors": errors})

    stored_control = configured_store.stored_model(DocumentControl, f"{prefix}.DocumentControl")
    stored_history = configured_store.stored_model(RevisionHistory, f"{prefix}.RevisionHistory")
    body_changed = body_result.action in (SaveAction.CREATED, SaveAction.UPDATED)
    first = old_body is None or stored_history is None
    version = document_version(body_result.version)
    sections = changed_section_ids(None if first else old_body["Value"], body)
    summary = revision_summary(first, sections, configured_sources(template, app_id))
    history, entry = next_history(stored_history, body_changed, version, summary, today)
    control = next_control(app_id, doc_type, template.name, stored_control, body_result.action, body_result.version, today)
    save_object(ConfiguredDocumentControlSaver(), f"{prefix}.DocumentControl", control, errors)
    save_object(ConfiguredRevisionHistorySaver(), f"{prefix}.RevisionHistory", history, errors)

    gaps = configured_gaps(template, app_id)
    stored_needs = configured_store.stored_model(MissingInfo, f"{prefix}.MissingInfo")
    needs, origin, skipped, note = choose_needs(app_id, template.name, gaps, stored_needs, writer)
    save_object(ConfiguredMissingInfoSaver(), f"{prefix}.MissingInfo",
                MissingInfo(gaps=gaps, needs=needs, gaps_hash=gaps_hash(gaps), needs_origin=origin), errors)

    written: list[str] = []
    if not errors:
        folder = output_dir() / "configured" / app_id
        write_if_changed(folder / f"{doc_type}.md", render_configured_markdown(app_id, doc_type), written)
        write_if_changed(folder / f"{doc_type}.missing.md", render_configured_needs(app_id, doc_type), written)
    return report.model_copy(update={
        "document_version": control.document_version, "revision_added": entry.summary if entry else "",
        "gap_count": len(gaps), "need_count": len(needs), "needs_origin": origin.value, "needs_skipped": skipped,
        "needs_note": note, "output_files": written, "errors": errors,
    })
