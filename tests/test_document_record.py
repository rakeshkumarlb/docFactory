import pytest
from pydantic import ValidationError

from docfactory.models.document_record import DocumentRecord
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "key": "Test.Outputs.Doc",
    "value": "{}",
    "hashcode": "abc123",
    "completeness": 50.0,
    "version": 1,
}

FULL = {
    "key": "Test.Outputs.Doc",
    "value": "{}",
    "hashcode": "abc123",
    "completeness": 50.0,
    "version": 1,
    "app_id": "Test",
}


def test_minimal_payload_is_valid():
    DocumentRecord.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = DocumentRecord.model_validate(FULL)
    assert DocumentRecord.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["key", "value", "hashcode", "completeness", "version"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        DocumentRecord.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        DocumentRecord.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = DocumentRecord.model_validate(MINIMAL)
    assert obj.app_id is None


@pytest.mark.parametrize("field", ["key"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        DocumentRecord.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["key", "value", "hashcode", "completeness", "version", "app_id"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        DocumentRecord.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
