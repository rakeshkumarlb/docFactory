from pathlib import Path

import pytest

from docfactory.build import build_document
from docfactory.documentmodels.overview_document import OverviewDocument
from docfactory.documentsaver.document_control_saver import DocumentControlSaver
from docfactory.documentsaver.overview_document_saver import OverviewDocumentSaver
from docfactory.documentsaver.revision_history_saver import RevisionHistorySaver
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.kpis_saver import KpisSaver
from docfactory.render import RenderError, render_markdown

pytestmark = pytest.mark.usefixtures("tmp_db")

APP = "TestApp"
GOLDEN = Path(__file__).parent / "golden" / "overview.md"

OVERVIEW_FACT = {
    "application_name": "TestApp",
    "purpose": "Does the one thing this test needs.",
    "business_overview": "Supports the test suite.",
    "target_users": ["Testers"],
    "key_capabilities": ["Run tests"],
    "business_criticality": "Tier 1",
}
KPIS_FACT = {"kpis": [{"name": "Pass rate", "definition": "Share of tests passing."}], "notes": "Reviewed weekly."}
CONTROL = {
    "document_id": "TestApp-OVR-001",
    "title": "TestApp Overview",
    "document_version": "1.0",
    "status": "Draft",
    "owner": "QA Lead",
    "approvers": ["Engineering Manager"],
    "created_date": "2024-01-15",
}
HISTORY = {"revisions": [{"version": "1.0", "date": "2024-01-15", "summary": "Initial draft created.", "author": "Jane Doe"}]}


def _seed_full_document():
    ApplicationOverviewSaver().save(f"{APP}.ApplicationOverview", OVERVIEW_FACT)
    KpisSaver().save("Shared.Kpis", KPIS_FACT)
    document, _ = build_document(OverviewDocument, APP)
    OverviewDocumentSaver().save(f"{APP}.Outputs.Overview", document.model_dump(mode="json"))
    DocumentControlSaver().save(f"{APP}.Outputs.Overview.DocumentControl", CONTROL)
    RevisionHistorySaver().save(f"{APP}.Outputs.Overview.RevisionHistory", HISTORY)


def test_render_matches_the_golden_file_and_is_deterministic():
    _seed_full_document()

    first = render_markdown(APP, "Overview")
    second = render_markdown(APP, "Overview")

    assert first == second
    assert first == GOLDEN.read_text(encoding="utf-8")


def test_missing_document_control_row_raises_a_clear_error():
    _seed_full_document()
    import sqlite3
    import os
    con = sqlite3.connect(os.environ["DOCFACTORY_DB"])
    con.execute("DELETE FROM DocumentOutputs WHERE DocumentKey = ?", (f"{APP}.Outputs.Overview.DocumentControl",))
    con.commit()
    con.close()

    with pytest.raises(RenderError, match="DocumentControl"):
        render_markdown(APP, "Overview")


def test_missing_revision_history_row_raises_a_clear_error():
    ApplicationOverviewSaver().save(f"{APP}.ApplicationOverview", OVERVIEW_FACT)
    document, _ = build_document(OverviewDocument, APP)
    OverviewDocumentSaver().save(f"{APP}.Outputs.Overview", document.model_dump(mode="json"))
    DocumentControlSaver().save(f"{APP}.Outputs.Overview.DocumentControl", CONTROL)

    with pytest.raises(RenderError, match="RevisionHistory"):
        render_markdown(APP, "Overview")


def test_unknown_doc_type_raises_a_clear_error():
    with pytest.raises(RenderError, match="doc_type"):
        render_markdown(APP, "NoSuchDoc")
