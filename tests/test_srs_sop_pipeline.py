import os
from pathlib import Path

import pytest

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

pytestmark = pytest.mark.usefixtures("tmp_db")

APP = "TestApp"
GOLDEN = Path(__file__).parent / "golden"

APP_FACTS = {
    "ApplicationOverview": (ApplicationOverviewSaver, {
        "application_name": "TestApp", "purpose": "Does the one thing this test needs.",
        "business_overview": "Supports the test suite.", "target_users": ["Testers"],
        "key_capabilities": ["Run tests"], "business_criticality": "Tier 1",
        "out_of_scope": ["Payroll processing"], "technology_summary": "Test stack.",
    }),
    "FunctionalRequirements": (FunctionalRequirementsSaver, {
        "summary": "Test functional scope.",
        "requirements": [{"id": "FR-TEST-1", "title": "Test requirement", "description": "The system shall pass the test.", "priority": "MUST",
                          "rationale": {"reason": "Test: self-evident"}, "acceptance_criteria": ["Test criterion one", "Test criterion two"]}],
        "out_of_scope": ["Test exclusion"],
    }),
    "NonFunctionalRequirements": (NonFunctionalRequirementsSaver, {
        "summary": "Test quality scope.",
        "requirements": [{"id": "NFR-TEST-1", "category": "PERFORMANCE", "statement": "The test shall finish quickly.", "target": "Under 1 second",
                          "priority": "SHOULD", "verification": "Test timing run"}],
    }),
    "Monitoring": (MonitoringSaver, {
        "monitoring_tools": ["Test monitoring tool"], "key_metrics": ["Test metric"],
        "alerts": [{"name": "Test alert", "condition": "Test condition", "severity": "P1", "response_action": "Follow 'SOP: Test runbook'", "notification_channel": "Test channel"}],
        "dashboards": ["Test dashboard"], "log_locations": ["logs/test"],
    }),
    "Support": (SupportSaver, {
        "support_model": "Test model",
        "contacts": [{"role": "Test role", "team": "Test team", "contact_channel": "Test channel", "support_hours": "Test hours", "escalates_to": "Test escalation"}],
        "escalation_path": "Test path", "incident_process": "Test process", "runbooks": ["runbooks/test.md"],
    }),
    "Sop": (SopSaver, {
        "procedures": [{"name": "SOP: Test runbook", "purpose": "Test purpose", "trigger": "Test alert fires", "frequency": "On demand", "roles": ["Test role"],
                        "prerequisites": ["Test prerequisite"], "steps": ["Test step one", "Test step two"], "verification": "Test verification", "escalation": "Test escalation"}],
        "notes": "Test alert set-up standard.",
    }),
}
SLO_FACT = {"objectives": [{"name": "Test objective", "definition": "Test definition", "target": "Test target", "measurement_window": "Test window",
                            "measurement_source": "Test source", "breach_consequence": "Test consequence"}], "notes": "Test SLO note."}

DOCUMENTS = {
    "SRS": (SrsDocument, SrsDocumentSaver),
    "SOP": (SopDocument, SopDocumentSaver),
}


def _control(doc_type):
    return {"document_id": f"TestApp-{doc_type}-001", "title": f"TestApp {doc_type}", "document_version": "1.0", "status": "Draft",
            "owner": "QA Lead", "approvers": ["Engineering Manager"], "created_date": "2024-01-15"}


def _history(doc_type):
    return {"revisions": [{"version": "1.0", "date": "2024-01-15", "summary": f"Initial {doc_type} draft created.", "author": "Jane Doe"}]}


def _seed_facts(skip=()):
    for name, (saver, payload) in APP_FACTS.items():
        if name not in skip:
            assert saver().save(f"{APP}.{name}", payload).ok, name
    assert SloSaver().save("Shared.Slo", SLO_FACT).ok


def test_full_facts_build_a_fully_answered_srs_with_no_missing_fields():
    _seed_facts()

    document, missing = build_document(SrsDocument, APP)

    assert missing == []
    assert document.functional_requirements.requirements[0].id == "FR-TEST-1"
    assert document.non_functional_requirements.requirements[0].category.value == "PERFORMANCE"
    assert document.service_levels.objectives[0].name == "Test objective"


def test_full_facts_build_a_fully_answered_sop_with_no_missing_fields():
    _seed_facts()

    document, missing = build_document(SopDocument, APP)

    assert missing == []
    assert document.monitoring.alerts[0].name == "Test alert"
    assert document.standard_operating_procedures.procedures[0].steps == ["Test step one", "Test step two"]
    assert document.standard_operating_procedures.notes == "Test alert set-up standard."


def test_missing_requirements_are_reported_with_their_question_and_source():
    _seed_facts(skip={"FunctionalRequirements"})

    document, missing = build_document(SrsDocument, APP)

    assert document.functional_requirements.requirements == []
    fields = {item.field: item for item in missing}
    assert {"functional_requirements.summary", "functional_requirements.requirements", "functional_requirements.out_of_scope"} <= set(fields)
    assert fields["functional_requirements.requirements"].expected_source == "FunctionalRequirements.requirements"
    assert fields["functional_requirements.requirements"].question
    assert not any(name.startswith("non_functional_requirements.") for name in fields)


def test_missing_sop_facts_are_reported_with_their_question_and_source():
    _seed_facts(skip={"Sop"})

    document, missing = build_document(SopDocument, APP)

    assert document.standard_operating_procedures.procedures == []
    fields = {item.field: item for item in missing}
    assert fields["standard_operating_procedures.procedures"].expected_source == "Sop.procedures"
    assert fields["standard_operating_procedures.procedures"].question


def test_a_missing_application_overview_still_builds_and_reports_its_fields():
    _seed_facts(skip={"ApplicationOverview"})

    document, missing = build_document(SopDocument, APP)

    assert document.application_summary.application_name == ""
    fields = {item.field: item for item in missing}
    assert fields["application_summary.purpose"].expected_source == "ApplicationOverview.purpose"


@pytest.mark.parametrize("doc_type", ["SRS", "SOP"])
def test_body_saves_and_renders_to_the_golden_file_deterministically(doc_type):
    model, body_saver = DOCUMENTS[doc_type]
    _seed_facts()
    document, _ = build_document(model, APP)
    prefix = f"{APP}.Outputs.{doc_type}"
    assert body_saver().save(prefix, document.model_dump(mode="json")).ok
    assert DocumentControlSaver().save(f"{prefix}.DocumentControl", _control(doc_type)).ok
    assert RevisionHistorySaver().save(f"{prefix}.RevisionHistory", _history(doc_type)).ok

    first = render_markdown(APP, doc_type)

    assert first == render_markdown(APP, doc_type)
    golden = GOLDEN / f"{doc_type.lower()}.md"
    if os.environ.get("UPDATE_GOLDEN"):
        golden.write_bytes(first.encode("utf-8"))
    assert first == golden.read_text(encoding="utf-8")
