import pytest

from docfactory.build import BuildError, build_document
from docfactory.documentmodels.documents.overview_document import OverviewDocument
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.kpis_saver import KpisSaver

pytestmark = pytest.mark.usefixtures("tmp_db")

APP = "TestApp"

FULL_OVERVIEW = {
    "application_name": "TestApp",
    "purpose": "Does the one thing this test needs.",
    "business_overview": "Supports the test suite.",
    "target_users": ["Testers"],
    "key_capabilities": ["Run tests"],
    "business_criticality": "Tier 1",
    "out_of_scope": ["Payroll processing"],
    "technology_summary": "Test stack.",
}

FULL_KPIS = {"kpis": [{"name": "Pass rate", "definition": "Share of tests passing."}], "notes": "Reviewed weekly."}


def test_full_facts_build_a_fully_answered_document_with_no_missing_fields():
    ApplicationOverviewSaver().save(f"{APP}.ApplicationOverview", FULL_OVERVIEW)
    KpisSaver().save("Shared.Kpis", FULL_KPIS)

    document, missing = build_document(OverviewDocument, APP)

    assert missing == []
    assert document.application_summary.application_name == "TestApp"
    assert document.application_summary.business_overview == "Supports the test suite."
    assert document.kpi_summary.kpis[0].name == "Pass rate"
    assert document.kpi_summary.notes == "Reviewed weekly."


def test_unanswered_and_absent_facts_are_left_at_default_and_reported_missing():
    ApplicationOverviewSaver().save(f"{APP}.ApplicationOverview", FULL_OVERVIEW | {"business_overview": ""})
    # Shared.Kpis is never saved: the whole kpi_summary section has no source fact.

    document, missing = build_document(OverviewDocument, APP)

    assert document.application_summary.business_overview == ""
    assert document.kpi_summary.kpis == [] and document.kpi_summary.notes == ""
    fields = {item.field for item in missing}
    assert fields == {"application_summary.business_overview", "kpi_summary.kpis", "kpi_summary.notes"}
    kpis_entry = next(item for item in missing if item.field == "kpi_summary.kpis")
    assert kpis_entry.expected_source == "Kpis.kpis" and kpis_entry.question


def test_build_is_deterministic():
    ApplicationOverviewSaver().save(f"{APP}.ApplicationOverview", FULL_OVERVIEW)
    KpisSaver().save("Shared.Kpis", FULL_KPIS)

    first, _ = build_document(OverviewDocument, APP)
    second, _ = build_document(OverviewDocument, APP)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_no_facts_at_all_still_build_a_document_with_every_field_missing():
    document, missing = build_document(OverviewDocument, APP)

    assert document.application_summary.application_name == "" and document.application_summary.purpose == ""
    fields = {item.field for item in missing}
    assert {"application_summary.application_name", "application_summary.purpose", "kpi_summary.kpis"} <= fields
    assert len(fields) == len(OverviewDocument.model_fields["application_summary"].annotation.model_fields) + 2


def test_a_wrongly_wired_binding_raises_a_build_error(monkeypatch):
    from docfactory import build
    monkeypatch.delitem(build.FACT_SPECS, "Kpis")
    with pytest.raises(BuildError, match="Kpis"):
        build_document(OverviewDocument, APP)
