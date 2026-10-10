"""Seeds ReadmeForge's ApplicationOverview and the Shared Kpis facts, stores and renders the Overview document.

Hard-coded, Phase 1 seed script (CLAUDE.md "Data flow"): no parsing of source documents, just tool calls.

    python -m seed.seed_readmeforge

Loads the three ReadmeForge ApplicationOverview samples and the three shared DevEx-KPI samples, each in
increasing completeness under its own key (CREATED, then two UPDATEDs), builds the Overview document body
from the stored facts, saves it together with a hard-coded DocumentControl and RevisionHistory
(caller-supplied, not knowledge facts), and renders the rows to output/ReadmeForge/Overview.md.
"""
import json
from pathlib import Path

from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.kpis_saver import KpisSaver
from seed.seed_document import store_document
from seed.seed_meta import SEED_META

ROOT = Path(__file__).resolve().parents[1]
APP = "ReadmeForge"
OVERVIEW_SAMPLES = ("readmeforge_minimal.json", "readmeforge_partial.json", "readmeforge_full.json")
KPIS_SAMPLES = ("shared_devex_kpis_minimal.json", "shared_devex_kpis_partial.json", "shared_devex_kpis_full.json")

DOCUMENT_CONTROL = {
    "document_id": "ReadmeForge-OVR-001",
    "title": "ReadmeForge Application Overview",
    "document_version": "1.1",
    "status": "Draft",
    "owner": "Head of Developer Experience",
    "approvers": ["Head of Developer Experience"],
    "created_date": "2026-09-27",
    "last_updated_date": "2026-09-27",
}
REVISION_HISTORY = {
    "revisions": [
        {
            "version": "1.0",
            "date": "2026-09-27",
            "summary": "Initial overview generated from the seeded ApplicationOverview facts.",
            "author": "docFactory seed",
        },
        {
            "version": "1.1",
            "date": "2026-09-27",
            "summary": "Added the KPI section, generated from the newly seeded Shared.Kpis facts.",
            "author": "docFactory seed",
        },
    ]
}


def _seed(saver, key: str, sample_dir: str, names: tuple[str, ...]) -> None:
    for name in names:
        payload = json.loads((ROOT / "samples" / "json" / sample_dir / name).read_text(encoding="utf-8"))
        result = saver.save(key, payload, meta=SEED_META)
        print(f"{name}: {result.action} version={result.version} completeness={result.completeness}")
        assert result.ok, result.errors


def main() -> None:
    _seed(ApplicationOverviewSaver(), f"{APP}.ApplicationOverview", "application_overview", OVERVIEW_SAMPLES)
    _seed(KpisSaver(), "Shared.Kpis", "kpis", KPIS_SAMPLES)

    store_document(APP, "Overview", DOCUMENT_CONTROL, REVISION_HISTORY)


if __name__ == "__main__":
    main()
