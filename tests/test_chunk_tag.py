import pytest
from pydantic import ValidationError

from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "chunk_no": 1,
    "entity": "Test-Entity",
    "origin": "rule",
}

FULL = {
    "chunk_no": 1,
    "entity": "Test-Entity",
    "origin": "rule",
    "score": 6,
    "evidence": "Test evidence",
}


def test_minimal_payload_is_valid():
    ChunkTag.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ChunkTag.model_validate(FULL)
    assert ChunkTag.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["chunk_no", "entity", "origin"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ChunkTag.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ChunkTag.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = ChunkTag.model_validate(MINIMAL)
    assert obj.score == 0
    assert obj.evidence == ''


@pytest.mark.parametrize("field", ["entity", "origin"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        ChunkTag.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["chunk_no", "entity", "origin", "score", "evidence"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        ChunkTag.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("value", [0, -1])
def test_chunk_no_below_one_is_rejected(value):
    with pytest.raises(ValidationError):
        ChunkTag.model_validate({**FULL, "chunk_no": value})


def test_completeness_counts_only_answered_fields():
    from docfactory.completeness import completeness

    # 5 fields: 3 mandatory answered, score/evidence at default -> 3/5
    assert completeness(ChunkTag.model_validate(MINIMAL)) == pytest.approx(60.0)
    assert completeness(ChunkTag.model_validate(FULL)) == pytest.approx(100.0)
