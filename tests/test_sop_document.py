import pytest
from pydantic import ValidationError

from docfactory.documentmodels.documents.sop_document import SopDocument
from docfactory.models.not_applicable import NotApplicable
from docfactory.documentmodels.entitybound.application_summary_section import ApplicationSummarySection
from docfactory.documentmodels.entitybound.monitoring_section import MonitoringSection
from docfactory.documentmodels.entitybound.sop_section import SopSection
from docfactory.documentmodels.entitybound.support_section import SupportSection

MINIMAL = {
    "application_summary": {"application_name": "Test-App", "purpose": "Test purpose statement."},
    "monitoring": {"monitoring_tools": ["Test monitoring tool"]},
    "support": {"support_model": "Test support model"},
    "standard_operating_procedures": {"notes": "Test notes."},
}

FULL = {
    "application_summary": {"application_name": "Test-App", "purpose": "Test purpose statement."},
    "monitoring": {"monitoring_tools": ["Test monitoring tool"]},
    "support": {"support_model": "Test support model"},
    "standard_operating_procedures": {"notes": "Test notes."},
}


def test_minimal_payload_is_valid():
    SopDocument.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SopDocument.model_validate(FULL)
    assert SopDocument.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["application_summary", "monitoring", "support", "standard_operating_procedures"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        SopDocument.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SopDocument.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field", ["application_summary", "monitoring", "support", "standard_operating_procedures"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SopDocument.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
