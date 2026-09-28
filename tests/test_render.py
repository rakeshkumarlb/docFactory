from pathlib import Path

import pytest

from docfactory.build import build_document
from docfactory.documentmodels.documents.overview_document import OverviewDocument
from docfactory.documentsaver.shared.document_control_saver import DocumentControlSaver
from docfactory.documentsaver.documents.overview_document_saver import OverviewDocumentSaver
from docfactory.documentsaver.shared.revision_history_saver import RevisionHistorySaver
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
    "out_of_scope": ["Payroll processing"],
    "technology_summary": "Test stack.",
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


def test_kpis_render_as_a_table_with_one_row_per_kpi_and_other_lists_stay_bulleted():
    ApplicationOverviewSaver().save(f"{APP}.ApplicationOverview", OVERVIEW_FACT)
    KpisSaver().save(
        "Shared.Kpis",
        {
            "kpis": [
                {"name": "Pass rate", "definition": "Share of tests passing.", "unit": "%"},
                {"name": "Escaped | pipe", "definition": "Has a | in it and a\nnewline.", "data_source": {"reason": "Tracked manually, no dashboard yet."}},
            ]
        },
    )
    document, _ = build_document(OverviewDocument, APP)
    OverviewDocumentSaver().save(f"{APP}.Outputs.Overview", document.model_dump(mode="json"))
    DocumentControlSaver().save(f"{APP}.Outputs.Overview.DocumentControl", CONTROL)
    RevisionHistorySaver().save(f"{APP}.Outputs.Overview.RevisionHistory", HISTORY)

    rendered = render_markdown(APP, "Overview")

    assert "| Name | Definition | Unit | Target | Current Value | Measurement Frequency | Owner | Data Source |" in rendered
    assert "| Pass rate | Share of tests passing. | % | _Not provided._ | _Not provided._ | _Not provided._ | _Not provided._ | _Not provided._ |" in rendered
    assert "Escaped \\| pipe" in rendered
    assert "Has a \\| in it and a newline." in rendered
    assert "_N/A — Tracked manually, no dashboard yet._" in rendered
    assert "\n1.\n" not in rendered
    assert "**Target Users:**\n- Testers" in rendered


def test_lists_inside_items_render_as_nested_lists_and_steps_are_numbered():
    from docfactory.models.sop_procedure import SopProcedure
    from docfactory.render import _item_lines

    item = SopProcedure(name="Test procedure", roles=["Test role"], steps=["Test step, with a comma", "Test step two"])

    lines = _item_lines(item)

    assert "  - **Roles:**" in lines and "    - Test role" in lines
    assert lines[lines.index("  - **Steps:**") + 1:][:2] == ["    1. Test step, with a comma", "    2. Test step two"]
    assert "  - **Prerequisites:** _Not provided._" in lines
