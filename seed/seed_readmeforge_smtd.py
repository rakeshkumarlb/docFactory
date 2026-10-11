"""Seeds every fact the SMTD needs for ReadmeForge, then builds and renders the SMTD document.

Hard-coded, Phase 1 seed script (CLAUDE.md "Data flow"): no parsing of source documents, just tool calls.

    python -m seed.seed_readmeforge_smtd

Saves the full ReadmeForge samples for the application-specific facts (ApplicationOverview, Architecture,
Environments, Deployment, Monitoring, BackupRecovery, Support, KnownErrors, Sop) and the full shared samples
(Kpis, Slo). Saving a payload that is already stored is a no-op (UNCHANGED), so the script can be re-run and
can be run before or after `seed.seed_readmeforge`. It then builds the SMTD body from the stored facts, saves
it with a hard-coded DocumentControl and RevisionHistory (caller-supplied, not knowledge facts), and renders the
three rows to output/ReadmeForge/SMTD.md, with the list of DocumentGap items (the gaps) in SMTD.missing.json.
"""
import json
from pathlib import Path

from seed.seed_document import store_document
from docfactory.bundle.bundle_store import BundleStore
from seed.seed_meta import SEED_META

ROOT = Path(__file__).resolve().parents[1]
APP = "ReadmeForge"

# (fact key, sample folder under samples/json/, sample file)
FACTS = (
    (f"{APP}.ApplicationOverview", "application_overview", "readmeforge_full.json"),
    (f"{APP}.Architecture", "architecture", "readmeforge_full.json"),
    (f"{APP}.Environments", "environments", "readmeforge_full.json"),
    (f"{APP}.Deployment", "deployment", "readmeforge_full.json"),
    (f"{APP}.Monitoring", "monitoring", "readmeforge_datadog.json"),
    (f"{APP}.BackupRecovery", "backup_recovery", "readmeforge_full.json"),
    (f"{APP}.Support", "support", "readmeforge_full.json"),
    (f"{APP}.KnownErrors", "known_errors", "readmeforge_full.json"),
    (f"{APP}.Sop", "sop", "readmeforge_datadog_runbooks.json"),
    ("Shared.Kpis", "kpis", "shared_devex_kpis_full.json"),
    ("Shared.Slo", "slo", "shared_platform_slo_full.json"),
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
    for key, folder, name in FACTS:
        payload = json.loads((ROOT / "samples" / "json" / folder / name).read_text(encoding="utf-8"))
        result = BundleStore().write_fact(key, payload, SEED_META)
        print(f"{key}: {result.action} version={result.version} completeness={result.completeness}")
        assert result.ok, result.errors

    store_document(APP, "SMTD", DOCUMENT_CONTROL, REVISION_HISTORY)


if __name__ == "__main__":
    main()
