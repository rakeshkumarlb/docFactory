import pytest
from pydantic import ValidationError

from docfactory.models.chunk_tag_proposal import ChunkTagProposal
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "chunk_no": 3,
    "reason": "test reason",
}

FULL = {
    "chunk_no": 3,
    "entities": ["Test-Entity"],
    "reason": "test reason",
}


def test_minimal_payload_is_valid():
    ChunkTagProposal.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ChunkTagProposal.model_validate(FULL)
    assert ChunkTagProposal.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["chunk_no", "reason"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ChunkTagProposal.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ChunkTagProposal.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ChunkTagProposal.model_validate(MINIMAL)
    assert obj.entities == []


@pytest.mark.parametrize("field", ["reason"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        ChunkTagProposal.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["chunk_no", "entities", "reason"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ChunkTagProposal.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("value", [0, -1])
def test_chunk_no_below_one_is_rejected(value):
    with pytest.raises(ValidationError):
        ChunkTagProposal.model_validate({**FULL, "chunk_no": value})


def test_empty_entities_list_is_a_valid_answer():
    assert ChunkTagProposal.model_validate({**FULL, "entities": []}).entities == []


@pytest.mark.parametrize("field,value", [("chunk_no", "x"), ("entities", "Architecture"), ("reason", 5)])
def test_wrong_type_is_rejected(field, value):
    with pytest.raises(ValidationError):
        ChunkTagProposal.model_validate({**FULL, field: value})
