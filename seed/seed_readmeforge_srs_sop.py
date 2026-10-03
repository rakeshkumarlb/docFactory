"""Seeds every fact the SRS and the SOP need for ReadmeForge, then builds and renders both documents.

Hard-coded, Phase 1 seed script (CLAUDE.md "Data flow"): no parsing of source documents, just tool calls.

    python -m seed.seed_readmeforge_srs_sop

The SOP describes ReadmeForge in production monitored by Datadog: the Monitoring sample holds the Datadog monitors
and the Sop sample holds five alert-driven runbooks plus the notes on how alerts are set up and documented.
Saving a payload that is already stored is a no-op (UNCHANGED), so the script can be re-run and can be run before
or after the other seed scripts. Each document body is built from the stored facts and saved with a hard-coded
DocumentControl and RevisionHistory (caller-supplied, not knowledge facts), then rendered to
output/ReadmeForge/<SRS|SOP>.md with the MissingInfo list in output/ReadmeForge/<SRS|SOP>.missing.json.
"""
import json
from pathlib import Path

from docfactory.build import build_document
from docfactory.documentmodels.documents.sop_document import SopDocument
from docfactory.documentmodels.documents.srs_document import SrsDocument
from docfactory.documentsaver.documents.sop_document_saver import SopDocumentSaver
from docfactory.documentsaver.documents.srs_document_saver import SrsDocumentSaver
from docfactory.documentsaver.shared.document_control_saver import DocumentControlSaver
from docfactory.documentsaver.shared.revision_history_saver import RevisionHistorySaver
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.functional_requirements_saver import FunctionalRequirementsSaver
from docfactory.entitysaver.monitoring_saver import MonitoringSaver
from docfactory.entitysaver.non_functional_requirements_saver import NonFunctionalRequirementsSaver
from docfactory.entitysaver.slo_saver import SloSaver
from docfactory.entitysaver.sop_saver import SopSaver
from docfactory.entitysaver.support_saver import SupportSaver
from docfactory.render import render_markdown

ROOT = Path(__file__).resolve().parents[1]
APP = "ReadmeForge"

# (saver, fact key, sample folder under samples/, sample file)
FACTS = (
    (ApplicationOverviewSaver, f"{APP}.ApplicationOverview", "application_overview", "readmeforge_full.json"),
    (FunctionalRequirementsSaver, f"{APP}.FunctionalRequirements", "functional_requirements", "readmeforge_full.json"),
    (NonFunctionalRequirementsSaver, f"{APP}.NonFunctionalRequirements", "non_functional_requirements", "readmeforge_full.json"),
    (SloSaver, "Shared.Slo", "slo", "shared_platform_slo_full.json"),
    (MonitoringSaver, f"{APP}.Monitoring", "monitoring", "readmeforge_datadog.json"),
    (SupportSaver, f"{APP}.Support", "support", "readmeforge_full.json"),
    (SopSaver, f"{APP}.Sop", "sop", "readmeforge_datadog_runbooks.json"),
)

# (doc type, document model, body saver, DocumentControl, RevisionHistory)
DOCUMENTS = (
    (
        "SRS", SrsDocument, SrsDocumentSaver,
        {
            "document_id": "ReadmeForge-SRS-001",
            "title": "ReadmeForge Software Requirements Specification",
            "document_version": "1.0",
            "status": "Draft",
            "owner": "ReadmeForge Product Owner",
            "approvers": ["Head of Developer Experience", "ReadmeForge Platform Engineering Lead"],
            "created_date": "2026-10-03",
            "last_updated_date": "2026-10-03",
        },
        {"revisions": [{"version": "1.0", "date": "2026-10-03", "summary": "Initial SRS generated from the seeded ReadmeForge facts.", "author": "docFactory seed"}]},
    ),
    (
        "SOP", SopDocument, SopDocumentSaver,
        {
            "document_id": "ReadmeForge-SOP-001",
            "title": "ReadmeForge Standard Operating Procedures (Datadog alert runbooks)",
            "document_version": "1.0",
            "status": "Draft",
            "owner": "ReadmeForge Platform Engineering Lead",
            "approvers": ["Head of Developer Experience", "ReadmeForge Platform Engineering Lead"],
            "created_date": "2026-10-03",
            "last_updated_date": "2026-10-03",
        },
        {"revisions": [{"version": "1.0", "date": "2026-10-03", "summary": "Initial SOP with five Datadog alert runbooks and the alert set-up standard.", "author": "docFactory seed"}]},
    ),
)


def main() -> None:
    for saver, key, folder, name in FACTS:
        payload = json.loads((ROOT / "samples" / folder / name).read_text(encoding="utf-8"))
        result = saver().save(key, payload)
        print(f"{key}: {result.action} version={result.version} completeness={result.completeness}")
        assert result.ok, result.errors

    output_dir = ROOT / "output" / APP
    output_dir.mkdir(parents=True, exist_ok=True)
    for doc_type, model, body_saver, control, history in DOCUMENTS:
        document, missing = build_document(model, APP)
        print(f"{doc_type} build_document: {len(missing)} missing field(s)")
        prefix = f"{APP}.Outputs.{doc_type}"
        results = (
            ("body", body_saver().save(prefix, document.model_dump(mode="json"))),
            ("DocumentControl", DocumentControlSaver().save(f"{prefix}.DocumentControl", control)),
            ("RevisionHistory", RevisionHistorySaver().save(f"{prefix}.RevisionHistory", history)),
        )
        for label, result in results:
            print(f"{doc_type} {label}: {result.action} completeness={result.completeness}")
            assert result.ok, result.errors
        (output_dir / f"{doc_type}.md").write_text(render_markdown(APP, doc_type), encoding="utf-8", newline="\n")
        (output_dir / f"{doc_type}.missing.json").write_text(
            json.dumps([item.model_dump(mode="json") for item in missing], indent=2), encoding="utf-8"
        )
        print(f"wrote {output_dir / (doc_type + '.md')}")


if __name__ == "__main__":
    main()
