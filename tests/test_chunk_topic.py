import pytest
from pydantic import ValidationError

from docfactory.models.chunk_topic import ChunkTopic
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "chunk_no": 1,
}

FULL = {
    "chunk_no": 1,
    "facts": ["Deployment"],
}


def test_minimal_payload_is_valid():
    ChunkTopic.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ChunkTopic.model_validate(FULL)
    assert ChunkTopic.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["chunk_no"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ChunkTopic.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ChunkTopic.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ChunkTopic.model_validate(MINIMAL)
    assert obj.facts == []


@pytest.mark.parametrize("field", ["chunk_no", "facts"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ChunkTopic.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
