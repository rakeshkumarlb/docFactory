import pytest
from pydantic import ValidationError

from docfactory.models.recognized_entity import RecognizedEntity
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "name": "Test Entity",
    "type": "Component",
}

FULL = {
    "name": "Test Entity",
    "type": "Component",
    "aliases": ["Test Alias"],
    "same_as": "Component/test-entity",
    "summary": "Test summary.",
    "chunks": [1],
    "reason": "Test reason.",
}


def test_minimal_payload_is_valid():
    RecognizedEntity.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = RecognizedEntity.model_validate(FULL)
    assert RecognizedEntity.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["name", "type"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        RecognizedEntity.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        RecognizedEntity.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = RecognizedEntity.model_validate(MINIMAL)
    assert obj.aliases == []
    assert obj.same_as is None
    assert obj.summary == ''
    assert obj.chunks == []
    assert obj.reason == ''


@pytest.mark.parametrize("field", ["name", "type"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        RecognizedEntity.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["name", "type", "aliases", "same_as", "summary", "chunks", "reason"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        RecognizedEntity.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
