"""Seeds every fact the SRS and the SOP need for ReadmeForge, then builds and renders both documents.

Hard-coded, Phase 1 seed script (CLAUDE.md "Data flow"): no parsing of source documents, just tool calls.

    python -m seed.seed_readmeforge_srs_sop

The SOP describes ReadmeForge in production monitored by Datadog: the Monitoring sample holds the Datadog monitors
and the Sop sample holds five alert-driven runbooks plus the notes on how alerts are set up and documented.
Saving a payload that is already stored is a no-op (UNCHANGED), so the script can be re-run and can be run before
or after the other seed scripts. Each document body is built from the stored facts and saved with a hard-coded
DocumentControl and RevisionHistory (caller-supplied, not knowledge facts), then rendered to
output/ReadmeForge/<SRS|SOP>.md with the list of DocumentGap items (the gaps) in <SRS|SOP>.missing.json.
"""
import json
from pathlib import Path

from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.functional_requirements_saver import FunctionalRequirementsSaver
from docfactory.entitysaver.monitoring_saver import MonitoringSaver
from docfactory.entitysaver.non_functional_requirements_saver import NonFunctionalRequirementsSaver
from docfactory.entitysaver.slo_saver import SloSaver
from docfactory.entitysaver.sop_saver import SopSaver
from docfactory.entitysaver.support_saver import SupportSaver
from seed.seed_document import store_document
from seed.seed_meta import SEED_META

ROOT = Path(__file__).resolve().parents[1]
APP = "ReadmeForge"

# (saver, fact key, sample folder under samples/json/, sample file)
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
        "SRS",
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
        "SOP",
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
        payload = json.loads((ROOT / "samples" / "json" / folder / name).read_text(encoding="utf-8"))
        result = saver().save(key, payload, meta=SEED_META)
        print(f"{key}: {result.action} version={result.version} completeness={result.completeness}")
        assert result.ok, result.errors

    for doc_type, control, history in DOCUMENTS:
        store_document(APP, doc_type, control, history)


if __name__ == "__main__":
    main()
