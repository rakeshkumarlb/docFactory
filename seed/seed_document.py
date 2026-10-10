"""Stores one ReadmeForge document the way the seed scripts do: body from the template and the stored facts, a hard-coded document control
and revision history (caller-supplied, not knowledge facts), then the Markdown and the list of gaps as views under output/<App>/."""
import json
from pathlib import Path

from docfactory.generation import document_store
from docfactory.generation.build_body import build_body
from docfactory.generation.template_gaps import template_gaps
from docfactory.generation.render_document import render_document_markdown
from docfactory.generation.template_loader import load_template
from docfactory.documentsaver.document_body_saver import DocumentBodySaver
from docfactory.documentsaver.document_control_saver import DocumentControlSaver
from docfactory.documentsaver.revision_history_saver import RevisionHistorySaver

ROOT = Path(__file__).resolve().parents[1]


def store_document(app_id: str, doc_type: str, control: dict, history: dict) -> None:
    template = load_template(doc_type)
    prefix = document_store.prefix(app_id, doc_type)
    body = build_body(template, app_id)
    gaps = template_gaps(template, app_id)
    print(f"{doc_type} build_body: {len(gaps)} gap(s)")
    results = (
        ("body", DocumentBodySaver().save(prefix, body.model_dump(mode="json"))),
        ("DocumentControl", DocumentControlSaver().save(f"{prefix}.DocumentControl", control)),
        ("RevisionHistory", RevisionHistorySaver().save(f"{prefix}.RevisionHistory", history)),
    )
    for label, result in results:
        print(f"{doc_type} {label}: {result.action} completeness={result.completeness}")
        assert result.ok, result.errors
    output_dir = ROOT / "output" / app_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{doc_type}.md").write_text(render_document_markdown(app_id, doc_type), encoding="utf-8", newline="\n")
    (output_dir / f"{doc_type}.missing.json").write_text(json.dumps([gap.model_dump(mode="json") for gap in gaps], indent=2), encoding="utf-8")
    print(f"wrote {output_dir / (doc_type + '.md')} and {output_dir / (doc_type + '.missing.json')}")
