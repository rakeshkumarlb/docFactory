import pytest
from pydantic import ValidationError

from docfactory.documentmodels.application_summary_section import ApplicationSummarySection
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "application_name": "KitchenHQ",
    "purpose": "Test purpose statement.",
}

FULL = {
    "application_name": "KitchenHQ",
    "purpose": "Test purpose statement.",
    "business_overview": "Test business overview.",
    "target_users": ["Test users"],
    "key_capabilities": ["Test capability"],
    "business_criticality": "Test criticality.",
    "out_of_scope": ["Test exclusion"],
    "technology_summary": "Test technology summary.",
}


def test_minimal_payload_is_valid():
    ApplicationSummarySection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ApplicationSummarySection.model_validate(FULL)
    assert ApplicationSummarySection.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["application_name", "purpose"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ApplicationSummarySection.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ApplicationSummarySection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ApplicationSummarySection.model_validate(MINIMAL)
    assert obj.business_overview == ''
    assert obj.target_users == []
    assert obj.key_capabilities == []
    assert obj.business_criticality == ''
    assert obj.out_of_scope == []
    assert obj.technology_summary == ''


@pytest.mark.parametrize("field", ["application_name", "purpose"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        ApplicationSummarySection.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["application_name", "purpose", "business_overview", "target_users", "key_capabilities", "business_criticality", "technology_summary"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ApplicationSummarySection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


def test_out_of_scope_accepts_not_applicable_with_a_reason():
    obj = ApplicationSummarySection.model_validate({**FULL, "out_of_scope": NotApplicable(reason="No exclusions were defined.")})
    assert isinstance(obj.out_of_scope, NotApplicable)
