"""The four documents render to the golden files: facts -> template -> stored rows (with caller-supplied control and history) -> Markdown."""
import os
from pathlib import Path

import pytest

from docfactory.generation import document_store
from docfactory.generation.build_body import build_body
from docfactory.generation.render_document import render_document_markdown
from docfactory.generation.template_loader import load_template
from docfactory.documentsaver.document_body_saver import DocumentBodySaver
from docfactory.documentsaver.document_control_saver import DocumentControlSaver
from docfactory.documentsaver.revision_history_saver import RevisionHistorySaver
from docfactory.render import RenderError, _item_lines
from docfactory.saver_resolution import entity_saver_for

pytestmark = pytest.mark.usefixtures("tmp_db")

APP = "TestApp"
GOLDEN = Path(__file__).parent / "golden"

OVERVIEW = {
    "application_name": "TestApp", "purpose": "Does the one thing this test needs.", "business_overview": "Supports the test suite.",
    "target_users": ["Testers"], "key_capabilities": ["Run tests"], "business_criticality": "Tier 1",
    "out_of_scope": ["Payroll processing"], "technology_summary": "Test stack.",
}
KPIS = {"kpis": [{"name": "Pass rate", "definition": "Share of tests passing."}], "notes": "Reviewed weekly."}
SLO = {"objectives": [{"name": "Test objective", "definition": "Test definition", "target": "Test target", "measurement_window": "Test window",
                       "measurement_source": "Test source", "breach_consequence": "Test consequence"}], "notes": "Test SLO note."}
SUPPORT = {
    "support_model": "Test model",
    "contacts": [{"role": "Test role", "team": "Test team", "contact_channel": "Test channel", "support_hours": "Test hours", "escalates_to": "Test escalation"}],
    "escalation_path": "Test path", "incident_process": "Test process", "runbooks": ["runbooks/test.md"],
}
SMTD_FACTS = {
    "ApplicationOverview": OVERVIEW,
    "Architecture": {
        "architecture_style": "Test layered style", "technology_stack": ["Test language"],
        "components": [{"name": "Test component", "purpose": "Test purpose", "technology": "Test tech", "owner": "Test team", "dependencies": ["Test store"]}],
        "data_stores": [{"name": "Test store", "store_type": "Test type", "technology": "Test tech", "contents": "Test data"}],
        "integrations": [{"name": "Test system", "direction": "outbound", "protocol": "Test protocol", "purpose": "Test purpose", "data_exchanged": "Test data", "authentication": "Test auth"}],
        "diagram_reference": "docs/test-diagram.md", "notes": "Test note.",
    },
    "Environments": {
        "environments": [{"name": "Test env", "purpose": "Test purpose", "hosting": "Test host", "url": "https://test.example", "access_control": "Test access", "notes": "Test note"}],
        "notes": "Test environments note.",
    },
    "Deployment": {"release_process": "Test release process", "ci_cd_tooling": "Test CI tool", "release_frequency": "Test frequency",
                   "rollback_procedure": "Test rollback", "configuration_management": "Test config management"},
    "Monitoring": {
        "monitoring_tools": ["Test tool"], "key_metrics": ["Test metric"],
        "alerts": [{"name": "Test alert", "condition": "Test condition", "severity": "Test severity", "response_action": "Test action", "notification_channel": "Test channel"}],
        "dashboards": ["Test dashboard"], "log_locations": ["logs/test"],
    },
    "BackupRecovery": {"backup_schedule": "Test schedule", "backup_retention": "Test retention", "backup_location": "Test location",
                       "restore_procedure": {"reason": "Test: stateless"}, "rpo": "Test RPO", "rto": "Test RTO", "disaster_recovery_plan": "Test DR plan"},
    "Support": SUPPORT,
    "KnownErrors": {
        "known_errors": [{"title": "Test error", "error_id": "KE-TEST", "symptoms": "Test symptoms", "cause": "Test cause", "workaround": "Test workaround",
                          "permanent_fix": {"reason": "Test: none planned"}, "severity": "Test severity", "status": "Test status", "related_ticket": {"reason": "Test: no ticket"}}],
        "notes": "Test known errors note.",
    },
    "Sop": {
        "procedures": [{"name": "Test procedure", "purpose": "Test purpose", "trigger": "Test trigger", "frequency": "Test frequency", "roles": ["Test role"],
                        "prerequisites": ["Test prerequisite"], "steps": ["Test step one", "Test step two"], "verification": "Test verification", "escalation": "Test escalation"}],
        "notes": "Test SOP note.",
    },
    "Slo": SLO,
    "Kpis": KPIS,
}
SRS_SOP_FACTS = {
    "ApplicationOverview": OVERVIEW,
    "FunctionalRequirements": {
        "summary": "Test functional scope.",
        "requirements": [{"id": "FR-TEST-1", "title": "Test requirement", "description": "The system shall pass the test.", "priority": "MUST",
                          "rationale": {"reason": "Test: self-evident"}, "acceptance_criteria": ["Test criterion one", "Test criterion two"]}],
        "out_of_scope": ["Test exclusion"],
    },
    "NonFunctionalRequirements": {
        "summary": "Test quality scope.",
        "requirements": [{"id": "NFR-TEST-1", "category": "PERFORMANCE", "statement": "The test shall finish quickly.", "target": "Under 1 second",
                          "priority": "SHOULD", "verification": "Test timing run"}],
    },
    "Monitoring": {
        "monitoring_tools": ["Test monitoring tool"], "key_metrics": ["Test metric"],
        "alerts": [{"name": "Test alert", "condition": "Test condition", "severity": "P1", "response_action": "Follow 'SOP: Test runbook'", "notification_channel": "Test channel"}],
        "dashboards": ["Test dashboard"], "log_locations": ["logs/test"],
    },
    "Support": SUPPORT,
    "Sop": {
        "procedures": [{"name": "SOP: Test runbook", "purpose": "Test purpose", "trigger": "Test alert fires", "frequency": "On demand", "roles": ["Test role"],
                        "prerequisites": ["Test prerequisite"], "steps": ["Test step one", "Test step two"], "verification": "Test verification", "escalation": "Test escalation"}],
        "notes": "Test alert set-up standard.",
    },
    "Slo": SLO,
}
# doc type -> (its facts, document control, revision history)
DOCUMENTS = {
    "Overview": ({"ApplicationOverview": OVERVIEW, "Kpis": KPIS}, "TestApp-OVR-001", "TestApp Overview", "Initial draft created."),
    "SMTD": (SMTD_FACTS, "TestApp-SMTD-001", "TestApp SMTD", "Initial draft created."),
    "SRS": (SRS_SOP_FACTS, "TestApp-SRS-001", "TestApp SRS", "Initial SRS draft created."),
    "SOP": (SRS_SOP_FACTS, "TestApp-SOP-001", "TestApp SOP", "Initial SOP draft created."),
}


def _seed(facts: dict) -> None:
    for name, payload in facts.items():
        saver = entity_saver_for(name)()
        key = f"Shared.{name}" if name in ("Slo", "Kpis") else f"{APP}.{name}"
        assert saver.save(key, payload).ok, name


def _store(doc_type: str, with_control: bool = True, with_history: bool = True) -> None:
    facts, document_id, title, summary = DOCUMENTS[doc_type]
    _seed(facts)
    prefix = document_store.prefix(APP, doc_type)
    result = DocumentBodySaver().save(prefix, build_body(load_template(doc_type), APP).model_dump(mode="json"))
    assert result.ok, result.errors
    control = {"document_id": document_id, "title": title, "document_version": "1.0", "status": "Draft",
               "owner": "QA Lead", "approvers": ["Engineering Manager"], "created_date": "2024-01-15"}
    history = {"revisions": [{"version": "1.0", "date": "2024-01-15", "summary": summary, "author": "Jane Doe"}]}
    if with_control:
        assert DocumentControlSaver().save(f"{prefix}.DocumentControl", control).ok
    if with_history:
        assert RevisionHistorySaver().save(f"{prefix}.RevisionHistory", history).ok


@pytest.mark.parametrize("doc_type", list(DOCUMENTS))
def test_the_document_renders_to_the_golden_file_deterministically(doc_type):
    _store(doc_type)

    first = render_document_markdown(APP, doc_type)

    assert first == render_document_markdown(APP, doc_type)
    golden = GOLDEN / f"{doc_type.lower()}.md"
    if os.environ.get("UPDATE_GOLDEN"):
        golden.write_bytes(first.encode("utf-8"))
    assert first == golden.read_text(encoding="utf-8")


def test_a_missing_revision_history_row_raises_a_clear_error():
    _store("Overview", with_history=False)

    with pytest.raises(RenderError, match="RevisionHistory"):
        render_document_markdown(APP, "Overview")


def test_kpis_render_as_a_table_with_one_row_per_kpi_and_other_lists_stay_bulleted():
    _seed({"ApplicationOverview": OVERVIEW})
    _seed({"Kpis": {"kpis": [
        {"name": "Pass rate", "definition": "Share of tests passing.", "unit": "%"},
        {"name": "Escaped | pipe", "definition": "Has a | in it and a\nnewline.", "data_source": {"reason": "Tracked manually, no dashboard yet."}},
    ]}})
    _store_rows_only("Overview")

    rendered = render_document_markdown(APP, "Overview")

    assert "| Name | Definition | Unit | Target | Current Value | Measurement Frequency | Owner | Data Source |" in rendered
    assert "| Pass rate | Share of tests passing. | % | _Not provided._ | _Not provided._ | _Not provided._ | _Not provided._ | _Not provided._ |" in rendered
    assert "Escaped \\| pipe" in rendered
    assert "Has a \\| in it and a newline." in rendered
    assert "_N/A — Tracked manually, no dashboard yet._" in rendered
    assert "\n1.\n" not in rendered
    assert "**Target Users:**\n- Testers" in rendered


def _store_rows_only(doc_type: str) -> None:
    """Body, control and history of `doc_type` over the facts already stored."""
    _, document_id, title, summary = DOCUMENTS[doc_type]
    prefix = document_store.prefix(APP, doc_type)
    assert DocumentBodySaver().save(prefix, build_body(load_template(doc_type), APP).model_dump(mode="json")).ok
    assert DocumentControlSaver().save(f"{prefix}.DocumentControl", {
        "document_id": document_id, "title": title, "document_version": "1.0", "status": "Draft"}).ok
    assert RevisionHistorySaver().save(f"{prefix}.RevisionHistory", {
        "revisions": [{"version": "1.0", "date": "2024-01-15", "summary": summary, "author": "Jane Doe"}]}).ok


def test_lists_inside_items_render_as_nested_lists_and_steps_are_numbered():
    from docfactory.entitymodels.items.sop_procedure import SopProcedure

    item = SopProcedure(name="Test procedure", roles=["Test role"], steps=["Test step, with a comma", "Test step two"])

    lines = _item_lines(item)

    assert "  - **Roles:**" in lines and "    - Test role" in lines
    assert lines[lines.index("  - **Steps:**") + 1:][:2] == ["    1. Test step, with a comma", "    2. Test step two"]
    assert "  - **Prerequisites:** _Not provided._" in lines
