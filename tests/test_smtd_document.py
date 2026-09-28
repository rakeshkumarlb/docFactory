import pytest
from pydantic import ValidationError

from docfactory.documentmodels.documents.smtd_document import SmtdDocument
from docfactory.models.not_applicable import NotApplicable
from docfactory.documentmodels.entitybound.application_summary_section import ApplicationSummarySection
from docfactory.documentmodels.entitybound.architecture_section import ArchitectureSection
from docfactory.documentmodels.entitybound.backup_recovery_section import BackupRecoverySection
from docfactory.documentmodels.entitybound.deployment_section import DeploymentSection
from docfactory.documentmodels.entitybound.environments_section import EnvironmentsSection
from docfactory.documentmodels.entitybound.known_errors_section import KnownErrorsSection
from docfactory.documentmodels.entitybound.kpi_summary_section import KpiSummarySection
from docfactory.documentmodels.entitybound.monitoring_section import MonitoringSection
from docfactory.documentmodels.entitybound.slo_section import SloSection
from docfactory.documentmodels.entitybound.sop_section import SopSection
from docfactory.documentmodels.entitybound.support_section import SupportSection

MINIMAL = {
    "application_summary": {"application_name": "Test-App", "purpose": "Test purpose statement."},
    "architecture": {"architecture_style": "Test architecture style"},
    "environments": {"notes": "Test notes."},
    "deployment": {"release_process": "Test release process."},
    "monitoring": {"monitoring_tools": ["Test monitoring tool"]},
    "backup_recovery": {"rpo": "Test RPO"},
    "support": {"support_model": "Test support model"},
    "known_errors": {"notes": "Test notes."},
    "standard_operating_procedures": {"notes": "Test notes."},
    "service_levels": {"notes": "Test notes."},
    "kpi_summary": {"notes": "Test notes."},
}

FULL = {
    "application_summary": {"application_name": "Test-App", "purpose": "Test purpose statement."},
    "architecture": {"architecture_style": "Test architecture style"},
    "environments": {"notes": "Test notes."},
    "deployment": {"release_process": "Test release process."},
    "monitoring": {"monitoring_tools": ["Test monitoring tool"]},
    "backup_recovery": {"rpo": "Test RPO"},
    "support": {"support_model": "Test support model"},
    "known_errors": {"notes": "Test notes."},
    "standard_operating_procedures": {"notes": "Test notes."},
    "service_levels": {"notes": "Test notes."},
    "kpi_summary": {"notes": "Test notes."},
}


def test_minimal_payload_is_valid():
    SmtdDocument.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SmtdDocument.model_validate(FULL)
    assert SmtdDocument.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["application_summary", "architecture", "environments", "deployment", "monitoring", "backup_recovery", "support", "known_errors", "standard_operating_procedures", "service_levels", "kpi_summary"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        SmtdDocument.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SmtdDocument.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field", ["application_summary", "architecture", "environments", "deployment", "monitoring", "backup_recovery", "support", "known_errors", "standard_operating_procedures", "service_levels", "kpi_summary"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SmtdDocument.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Composition (hand-written) ---
def test_body_holds_the_eleven_sections_in_order_and_no_control_parts():
    assert list(SmtdDocument.model_fields) == [
        "application_summary", "architecture", "environments", "deployment", "monitoring",
        "backup_recovery", "support", "known_errors", "standard_operating_procedures",
        "service_levels", "kpi_summary",
    ]
    for field in SmtdDocument.model_fields.values():
        assert field.json_schema_extra["binding"] == "composed"
