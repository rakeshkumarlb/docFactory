import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.functional_requirements_section import FunctionalRequirementsSection
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.requirement import Requirement

MINIMAL = {}

FULL = {
    "summary": "Test summary",
    "requirements": [{"id": "TEST-1", "title": "Test title", "description": "Test description"}],
    "out_of_scope": ["Test exclusion"],
}


def test_minimal_payload_is_valid():
    FunctionalRequirementsSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FunctionalRequirementsSection.model_validate(FULL)
    assert FunctionalRequirementsSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FunctionalRequirementsSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = FunctionalRequirementsSection.model_validate(MINIMAL)
    assert obj.summary == ''
    assert obj.requirements == []
    assert obj.out_of_scope == []


@pytest.mark.parametrize("field", ["out_of_scope"])
def test_not_applicable_is_accepted_where_allowed(field):
    FunctionalRequirementsSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["summary", "requirements"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FunctionalRequirementsSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
