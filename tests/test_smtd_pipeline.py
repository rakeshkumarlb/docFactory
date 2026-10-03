import os
from pathlib import Path

import pytest

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

pytestmark = pytest.mark.usefixtures("tmp_db")

APP = "TestApp"
GOLDEN = Path(__file__).parent / "golden" / "smtd.md"

APP_FACTS = {
    "ApplicationOverview": (ApplicationOverviewSaver, {
        "application_name": "TestApp", "purpose": "Does the one thing this test needs.",
        "business_overview": "Supports the test suite.", "target_users": ["Testers"],
        "key_capabilities": ["Run tests"], "business_criticality": "Tier 1",
        "out_of_scope": ["Payroll processing"], "technology_summary": "Test stack.",
    }),
    "Architecture": (ArchitectureSaver, {
        "architecture_style": "Test layered style", "technology_stack": ["Test language"],
        "components": [{"name": "Test component", "purpose": "Test purpose", "technology": "Test tech", "owner": "Test team", "dependencies": ["Test store"]}],
        "data_stores": [{"name": "Test store", "store_type": "Test type", "technology": "Test tech", "contents": "Test data"}],
        "integrations": [{"name": "Test system", "direction": "outbound", "protocol": "Test protocol", "purpose": "Test purpose", "data_exchanged": "Test data", "authentication": "Test auth"}],
        "diagram_reference": "docs/test-diagram.md", "notes": "Test note.",
    }),
    "Environments": (EnvironmentsSaver, {
        "environments": [{"name": "Test env", "purpose": "Test purpose", "hosting": "Test host", "url": "https://test.example", "access_control": "Test access", "notes": "Test note"}],
        "notes": "Test environments note.",
    }),
    "Deployment": (DeploymentSaver, {
        "release_process": "Test release process", "ci_cd_tooling": "Test CI tool", "release_frequency": "Test frequency",
        "rollback_procedure": "Test rollback", "configuration_management": "Test config management",
    }),
    "Monitoring": (MonitoringSaver, {
        "monitoring_tools": ["Test tool"], "key_metrics": ["Test metric"],
        "alerts": [{"name": "Test alert", "condition": "Test condition", "severity": "Test severity", "response_action": "Test action", "notification_channel": "Test channel"}],
        "dashboards": ["Test dashboard"], "log_locations": ["logs/test"],
    }),
    "BackupRecovery": (BackupRecoverySaver, {
        "backup_schedule": "Test schedule", "backup_retention": "Test retention", "backup_location": "Test location",
        "restore_procedure": {"reason": "Test: stateless"}, "rpo": "Test RPO", "rto": "Test RTO", "disaster_recovery_plan": "Test DR plan",
    }),
    "Support": (SupportSaver, {
        "support_model": "Test model",
        "contacts": [{"role": "Test role", "team": "Test team", "contact_channel": "Test channel", "support_hours": "Test hours", "escalates_to": "Test escalation"}],
        "escalation_path": "Test path", "incident_process": "Test process", "runbooks": ["runbooks/test.md"],
    }),
    "KnownErrors": (KnownErrorsSaver, {
        "known_errors": [{"title": "Test error", "error_id": "KE-TEST", "symptoms": "Test symptoms", "cause": "Test cause", "workaround": "Test workaround",
                          "permanent_fix": {"reason": "Test: none planned"}, "severity": "Test severity", "status": "Test status", "related_ticket": {"reason": "Test: no ticket"}}],
        "notes": "Test known errors note.",
    }),
    "Sop": (SopSaver, {
        "procedures": [{"name": "Test procedure", "purpose": "Test purpose", "trigger": "Test trigger", "frequency": "Test frequency", "roles": ["Test role"],
                        "prerequisites": ["Test prerequisite"], "steps": ["Test step one", "Test step two"], "verification": "Test verification", "escalation": "Test escalation"}],
        "notes": "Test SOP note.",
    }),
}
SLO_FACT = {"objectives": [{"name": "Test objective", "definition": "Test definition", "target": "Test target", "measurement_window": "Test window",
                            "measurement_source": "Test source", "breach_consequence": "Test consequence"}], "notes": "Test SLO note."}
KPIS_FACT = {"kpis": [{"name": "Pass rate", "definition": "Share of tests passing."}], "notes": "Reviewed weekly."}
CONTROL = {"document_id": "TestApp-SMTD-001", "title": "TestApp SMTD", "document_version": "1.0", "status": "Draft",
           "owner": "QA Lead", "approvers": ["Engineering Manager"], "created_date": "2024-01-15"}
HISTORY = {"revisions": [{"version": "1.0", "date": "2024-01-15", "summary": "Initial draft created.", "author": "Jane Doe"}]}


def _seed_facts(skip=()):
    for name, (saver, payload) in APP_FACTS.items():
        if name not in skip:
            assert saver().save(f"{APP}.{name}", payload).ok, name
    assert SloSaver().save("Shared.Slo", SLO_FACT).ok
    assert KpisSaver().save("Shared.Kpis", KPIS_FACT).ok


def test_full_facts_build_a_fully_answered_smtd_with_no_missing_fields():
    _seed_facts()

    document, missing = build_document(SmtdDocument, APP)

    assert missing == []
    assert document.architecture.components[0].name == "Test component"
    assert document.backup_recovery.restore_procedure.reason == "Test: stateless"
    assert document.standard_operating_procedures.procedures[0].steps == ["Test step one", "Test step two"]
    assert document.service_levels.objectives[0].name == "Test objective"


def test_missing_facts_are_reported_with_their_question_and_source():
    _seed_facts(skip={"KnownErrors", "Deployment"})

    document, missing = build_document(SmtdDocument, APP)

    assert document.known_errors.known_errors == []
    fields = {item.field: item for item in missing}
    assert {"known_errors.known_errors", "known_errors.notes", "deployment.release_process", "deployment.rollback_procedure"} <= set(fields)
    assert fields["known_errors.known_errors"].expected_source == "KnownErrors.known_errors"
    assert fields["deployment.release_process"].question
    assert not any(name.startswith(("architecture.", "support.")) for name in fields)


def test_smtd_body_saves_and_renders_to_the_golden_file_deterministically():
    _seed_facts()
    document, _ = build_document(SmtdDocument, APP)
    assert SmtdDocumentSaver().save(f"{APP}.Outputs.SMTD", document.model_dump(mode="json")).ok
    assert DocumentControlSaver().save(f"{APP}.Outputs.SMTD.DocumentControl", CONTROL).ok
    assert RevisionHistorySaver().save(f"{APP}.Outputs.SMTD.RevisionHistory", HISTORY).ok

    first = render_markdown(APP, "SMTD")

    assert first == render_markdown(APP, "SMTD")
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.write_bytes(first.encode("utf-8"))
    assert first == GOLDEN.read_text(encoding="utf-8")
