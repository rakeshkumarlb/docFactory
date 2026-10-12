import pytest
from pydantic import ValidationError

from docfactory.models.entity_evidence import EntityEvidence
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "resource": "Test/references/test.md",
    "chunk_no": 1,
}

FULL = {
    "resource": "Test/references/test.md",
    "chunk_no": 1,
    "heading": "Test heading",
    "text_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
}


def test_minimal_payload_is_valid():
    EntityEvidence.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = EntityEvidence.model_validate(FULL)
    assert EntityEvidence.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["resource", "chunk_no"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        EntityEvidence.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        EntityEvidence.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = EntityEvidence.model_validate(MINIMAL)
    assert obj.heading == ''
    assert obj.text_hash == ''


@pytest.mark.parametrize("field", ["resource"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        EntityEvidence.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["resource", "chunk_no", "heading", "text_hash"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        EntityEvidence.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
