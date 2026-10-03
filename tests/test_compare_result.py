import pytest
from pydantic import ValidationError

from docfactory.models.compare_result import CompareResult
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.file_action import FileAction

MINIMAL = {
    "target_path": "Test-Scope/test-file.txt",
    "action": FileAction.NEW,
    "incoming_hashcode": "0" * 64,
}

FULL = {
    "target_path": "Test-Scope/test-file.txt",
    "action": FileAction.NEW,
    "incoming_hashcode": "0" * 64,
    "stored_hashcode": "1" * 64,
    "stored_version": 2,
}


def test_minimal_payload_is_valid():
    CompareResult.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = CompareResult.model_validate(FULL)
    assert CompareResult.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["target_path", "action", "incoming_hashcode"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        CompareResult.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        CompareResult.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = CompareResult.model_validate(MINIMAL)
    assert obj.stored_hashcode is None
    assert obj.stored_version is None


@pytest.mark.parametrize("field", ["target_path", "incoming_hashcode"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        CompareResult.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["target_path", "action", "incoming_hashcode", "stored_hashcode", "stored_version"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        CompareResult.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
