import pytest
from pydantic import ValidationError

from docfactory.completeness import completeness
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "chunk_no": 1,
    "heading": "Test heading",
    "text": "Test text | cell",
    "text_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
}

FULL = {
    "chunk_no": 1,
    "heading": "Test heading",
    "page_from": 3,
    "page_to": 4,
    "text": "Test text | cell",
    "text_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
}


def test_minimal_payload_is_valid():
    DocChunk.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = DocChunk.model_validate(FULL)
    assert DocChunk.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["chunk_no", "heading", "text", "text_hash"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        DocChunk.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        DocChunk.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = DocChunk.model_validate(MINIMAL)
    assert obj.page_from is None
    assert obj.page_to is None


@pytest.mark.parametrize("field", ["heading", "text"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        DocChunk.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["text_hash"])
def test_text_not_matching_the_pattern_is_rejected(field):
    with pytest.raises(ValidationError):
        DocChunk.model_validate({**FULL, field: "not matching the pattern"})


@pytest.mark.parametrize("field", ["chunk_no", "heading", "page_from", "page_to", "text", "text_hash"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        DocChunk.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["chunk_no", "page_from", "page_to"])
@pytest.mark.parametrize("value", [0, -1])
def test_numbers_below_one_are_rejected(field, value):
    with pytest.raises(ValidationError):
        DocChunk.model_validate({**FULL, field: value})


def test_text_hash_must_be_64_lowercase_hex():
    for bad in ["0123", "A" * 64, "g" * 64, "a" * 65]:
        with pytest.raises(ValidationError):
            DocChunk.model_validate({**FULL, "text_hash": bad})


def test_completeness_counts_only_answered_fields():
    # 6 fields: 4 mandatory answered, page_from/page_to at default -> 4/6 = 66.67
    assert completeness(DocChunk.model_validate(MINIMAL)) == pytest.approx(4 / 6 * 100)
    # all 6 answered -> 100
    assert completeness(DocChunk.model_validate(FULL)) == pytest.approx(100.0)
