import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.non_functional_requirements_section import NonFunctionalRequirementsSection
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.non_functional_requirement import NonFunctionalRequirement

MINIMAL = {}

FULL = {
    "summary": "Test summary",
    "requirements": [{"id": "TEST-1", "category": "PERFORMANCE", "statement": "Test statement"}],
}


def test_minimal_payload_is_valid():
    NonFunctionalRequirementsSection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = NonFunctionalRequirementsSection.model_validate(FULL)
    assert NonFunctionalRequirementsSection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        NonFunctionalRequirementsSection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = NonFunctionalRequirementsSection.model_validate(MINIMAL)
    assert obj.summary == ''
    assert obj.requirements == []


@pytest.mark.parametrize("field", ["summary", "requirements"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        NonFunctionalRequirementsSection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
