import pytest
from pydantic import ValidationError

from docfactory.models.save_error import SaveError
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "path": "environments.0.name",
    "message": "Field required",
    "error_type": "missing",
}

FULL = {
    "path": "environments.0.name",
    "message": "Field required",
    "error_type": "missing",
    "received": "abc",
    "expected": "a valid string",
    "field_description": "Name of the environment",
    "question": "What is the name of the environment?",
}


def test_minimal_payload_is_valid():
    SaveError.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SaveError.model_validate(FULL)
    assert SaveError.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["path", "message", "error_type"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        SaveError.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SaveError.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = SaveError.model_validate(MINIMAL)
    assert obj.received is None
    assert obj.expected is None
    assert obj.field_description is None
    assert obj.question is None


@pytest.mark.parametrize("field", ["path", "message", "error_type"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        SaveError.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["path", "message", "error_type", "received", "expected", "field_description", "question"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SaveError.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
