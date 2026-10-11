"""Stores one ReadmeForge document the way the seed scripts do: body from the template and the stored facts, a hard-coded document control
and revision history (caller-supplied, not knowledge facts), then the Markdown and the list of gaps as views under output/<App>/."""
import json

from docfactory.generation.build_body import build_body
from docfactory.generation.document_parts import BODY, CONTROL, HISTORY
from docfactory.generation.document_state_store import DocumentStateStore
from docfactory.generation.generation_steps import output_dir
from docfactory.generation.render_document import render_document_markdown
from docfactory.generation.template_gaps import template_gaps
from docfactory.generation.template_loader import load_template


def store_document(app_id: str, doc_type: str, control: dict, history: dict) -> None:
    template = load_template(doc_type)
    store = DocumentStateStore()
    body = build_body(template, app_id)
    gaps = template_gaps(template, app_id)
    print(f"{doc_type} build_body: {len(gaps)} gap(s)")
    results = (
        ("body", store.save(app_id, doc_type, BODY, body)),
        ("DocumentControl", store.save(app_id, doc_type, CONTROL, control)),
        ("RevisionHistory", store.save(app_id, doc_type, HISTORY, history)),
    )
    for label, result in results:
        print(f"{doc_type} {label}: {result.action} completeness={result.completeness}")
        assert result.ok, result.errors
    folder = output_dir() / app_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{doc_type}.md").write_text(render_document_markdown(app_id, doc_type), encoding="utf-8", newline="\n")
    (folder / f"{doc_type}.missing.json").write_text(json.dumps([gap.model_dump(mode="json") for gap in gaps], indent=2), encoding="utf-8")
    print(f"wrote {folder / (doc_type + '.md')} and {folder / (doc_type + '.missing.json')}")
