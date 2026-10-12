import pytest
from pydantic import ValidationError

from docfactory.models.entity_record import EntityRecord
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.entity_evidence import EntityEvidence
from docfactory.models.entity_link import EntityLink

MINIMAL = {
    "entity_id": "Component/test-entity",
    "scope": "TestApp",
    "type": "Component",
    "name": "Test Entity",
}

FULL = {
    "entity_id": "Component/test-entity",
    "scope": "TestApp",
    "type": "Component",
    "name": "Test Entity",
    "aliases": ["Test Alias"],
    "summary": "Test summary.",
    "evidence": [],
    "links": [],
}


def test_minimal_payload_is_valid():
    EntityRecord.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = EntityRecord.model_validate(FULL)
    assert EntityRecord.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["entity_id", "scope", "type", "name"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        EntityRecord.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        EntityRecord.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = EntityRecord.model_validate(MINIMAL)
    assert obj.aliases == []
    assert obj.summary == ''
    assert obj.evidence == []
    assert obj.links == []


@pytest.mark.parametrize("field", ["entity_id", "scope", "type", "name"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        EntityRecord.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["entity_id", "scope", "type", "name", "aliases", "summary", "evidence", "links"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        EntityRecord.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
