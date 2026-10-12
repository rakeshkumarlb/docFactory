import pytest
from pydantic import ValidationError

from docfactory.models.resolution_group import ResolutionGroup
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "keep": "Component/test-a",
}

FULL = {
    "keep": "Component/test-a",
    "same": ["Component/test-b"],
    "reason": "Test reason.",
}


def test_minimal_payload_is_valid():
    ResolutionGroup.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ResolutionGroup.model_validate(FULL)
    assert ResolutionGroup.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["keep"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ResolutionGroup.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ResolutionGroup.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ResolutionGroup.model_validate(MINIMAL)
    assert obj.same == []
    assert obj.reason == ''


@pytest.mark.parametrize("field", ["keep"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        ResolutionGroup.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["keep", "same", "reason"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ResolutionGroup.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
