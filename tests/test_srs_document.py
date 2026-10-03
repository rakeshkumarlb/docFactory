import pytest
from pydantic import ValidationError

from docfactory.documentmodels.documents.srs_document import SrsDocument
from docfactory.models.not_applicable import NotApplicable
from docfactory.documentmodels.entitybound.application_summary_section import ApplicationSummarySection
from docfactory.documentmodels.entitybound.functional_requirements_section import FunctionalRequirementsSection
from docfactory.documentmodels.entitybound.non_functional_requirements_section import NonFunctionalRequirementsSection
from docfactory.documentmodels.entitybound.slo_section import SloSection

MINIMAL = {
    "application_summary": {"application_name": "Test-App", "purpose": "Test purpose statement."},
    "functional_requirements": {"summary": "Test summary"},
    "non_functional_requirements": {"summary": "Test summary"},
    "service_levels": {"notes": "Test notes."},
}

FULL = {
    "application_summary": {"application_name": "Test-App", "purpose": "Test purpose statement."},
    "functional_requirements": {"summary": "Test summary"},
    "non_functional_requirements": {"summary": "Test summary"},
    "service_levels": {"notes": "Test notes."},
}


def test_minimal_payload_is_valid():
    SrsDocument.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SrsDocument.model_validate(FULL)
    assert SrsDocument.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["application_summary", "functional_requirements", "non_functional_requirements", "service_levels"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        SrsDocument.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SrsDocument.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field", ["application_summary", "functional_requirements", "non_functional_requirements", "service_levels"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SrsDocument.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
