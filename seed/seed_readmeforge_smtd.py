"""Seeds every fact the SMTD needs for ReadmeForge, then builds and renders the SMTD document.

Hard-coded, Phase 1 seed script (CLAUDE.md "Data flow"): no parsing of source documents, just tool calls.

    python -m seed.seed_readmeforge_smtd

Saves the full ReadmeForge samples for the application-specific facts (ApplicationOverview, Architecture,
Environments, Deployment, Monitoring, BackupRecovery, Support, KnownErrors, Sop) and the full shared samples
(Kpis, Slo). Saving a payload that is already stored is a no-op (UNCHANGED), so the script can be re-run and
can be run before or after `seed.seed_readmeforge`. It then builds the SMTD body from the stored facts, saves
it with a hard-coded DocumentControl and RevisionHistory (caller-supplied, not knowledge facts), and renders the
three rows to output/ReadmeForge/SMTD.md, with the list of DocumentGap items (the gaps build_document found) in output/ReadmeForge/SMTD.missing.json.
"""
import json
from pathlib import Path

from docfactory.build import build_document
from docfactory.documentmodels.documents.smtd_document import SmtdDocument
from docfactory.documentsaver.documents.smtd_document_saver import SmtdDocumentSaver
from docfactory.documentsaver.shared.document_control_saver import DocumentControlSaver
from docfactory.documentsaver.shared.revision_history_saver import RevisionHistorySaver
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.architecture_saver import ArchitectureSaver
from docfactory.entitysaver.backup_recovery_saver import BackupRecoverySaver
from docfactory.entitysaver.deployment_saver import DeploymentSaver
from docfactory.entitysaver.environments_saver import EnvironmentsSaver
from docfactory.entitysaver.known_errors_saver import KnownErrorsSaver
from docfactory.entitysaver.kpis_saver import KpisSaver
from docfactory.entitysaver.monitoring_saver import MonitoringSaver
from docfactory.entitysaver.slo_saver import SloSaver
from docfactory.entitysaver.sop_saver import SopSaver
from docfactory.entitysaver.support_saver import SupportSaver
from docfactory.render import render_markdown
from seed.seed_meta import SEED_META

ROOT = Path(__file__).resolve().parents[1]
APP = "ReadmeForge"

# (saver, fact key, sample folder under samples/json/, sample file)
FACTS = (
    (ApplicationOverviewSaver, f"{APP}.ApplicationOverview", "application_overview", "readmeforge_full.json"),
    (ArchitectureSaver, f"{APP}.Architecture", "architecture", "readmeforge_full.json"),
    (EnvironmentsSaver, f"{APP}.Environments", "environments", "readmeforge_full.json"),
    (DeploymentSaver, f"{APP}.Deployment", "deployment", "readmeforge_full.json"),
    (MonitoringSaver, f"{APP}.Monitoring", "monitoring", "readmeforge_datadog.json"),
    (BackupRecoverySaver, f"{APP}.BackupRecovery", "backup_recovery", "readmeforge_full.json"),
    (SupportSaver, f"{APP}.Support", "support", "readmeforge_full.json"),
    (KnownErrorsSaver, f"{APP}.KnownErrors", "known_errors", "readmeforge_full.json"),
    (SopSaver, f"{APP}.Sop", "sop", "readmeforge_datadog_runbooks.json"),
    (KpisSaver, "Shared.Kpis", "kpis", "shared_devex_kpis_full.json"),
    (SloSaver, "Shared.Slo", "slo", "shared_platform_slo_full.json"),
)

DOCUMENT_CONTROL = {
    "document_id": "ReadmeForge-SMTD-001",
    "title": "ReadmeForge System Maintenance and Technical Document",
    "document_version": "1.0",
    "status": "Draft",
    "owner": "ReadmeForge Platform Engineering Lead",
    "approvers": ["Head of Developer Experience", "ReadmeForge Platform Engineering Lead"],
    "created_date": "2026-09-28",
    "last_updated_date": "2026-09-28",
}
REVISION_HISTORY = {
    "revisions": [
        {
            "version": "1.0",
            "date": "2026-09-28",
            "summary": "Initial SMTD generated from the seeded ReadmeForge facts (Azure Container Apps, four India locations).",
            "author": "docFactory seed",
        }
    ]
}


def main() -> None:
    for saver, key, folder, name in FACTS:
        payload = json.loads((ROOT / "samples" / "json" / folder / name).read_text(encoding="utf-8"))
        result = saver().save(key, payload, meta=SEED_META)
        print(f"{key}: {result.action} version={result.version} completeness={result.completeness}")
        assert result.ok, result.errors

    document, missing = build_document(SmtdDocument, APP)
    print(f"build_document: {len(missing)} missing field(s)")

    body_result = SmtdDocumentSaver().save(f"{APP}.Outputs.SMTD", document.model_dump(mode="json"))
    control_result = DocumentControlSaver().save(f"{APP}.Outputs.SMTD.DocumentControl", DOCUMENT_CONTROL)
    history_result = RevisionHistorySaver().save(f"{APP}.Outputs.SMTD.RevisionHistory", REVISION_HISTORY)
    for label, result in (("body", body_result), ("DocumentControl", control_result), ("RevisionHistory", history_result)):
        print(f"{label}: {result.action} completeness={result.completeness}")
        assert result.ok, result.errors

    output_dir = ROOT / "output" / APP
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "SMTD.md").write_text(render_markdown(APP, "SMTD"), encoding="utf-8", newline="\n")
    (output_dir / "SMTD.missing.json").write_text(
        json.dumps([item.model_dump(mode="json") for item in missing], indent=2), encoding="utf-8"
    )
    print(f"wrote {output_dir / 'SMTD.md'} and {output_dir / 'SMTD.missing.json'}")


if __name__ == "__main__":
    main()
