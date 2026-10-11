import pytest
from pydantic import ValidationError

from docfactory.models.not_applicable import NotApplicable
from docfactory.models.source_chunk import SourceChunk

FULL = {"chunk_no": 3, "heading": "3. Features > 3.1. Login", "text_hash": "a" * 64}


def test_a_full_payload_is_valid_and_round_trips():
    obj = SourceChunk.model_validate(FULL)
    assert SourceChunk.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", list(FULL))
def test_missing_mandatory_field_is_rejected(field):
    with pytest.raises(ValidationError) as caught:
        SourceChunk.model_validate({k: v for k, v in FULL.items() if k != field})
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SourceChunk.model_validate({**FULL, "text": "the chunk text is never stored here"})


@pytest.mark.parametrize("field,value", [("chunk_no", 0), ("heading", ""), ("text_hash", "not a hash"), ("text_hash", "A" * 64)])
def test_values_outside_the_constraints_are_rejected(field, value):
    with pytest.raises(ValidationError):
        SourceChunk.model_validate({**FULL, field: value})


@pytest.mark.parametrize("field", list(FULL))
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SourceChunk.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
