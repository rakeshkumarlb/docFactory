import pytest
from pydantic import ValidationError

from docfactory.models.not_applicable import NotApplicable
from docfactory.models.source_record import SourceRecord

MINIMAL = {"path": "Test-App/references/test-file.pdf", "hashcode": "0" * 64, "version": 1, "timestamp": "2026-01-01T00:00:00+00:00"}
FULL = {
    **MINIMAL,
    "chunks": [{"chunk_no": 1, "heading": "1. Introduction", "text_hash": "1" * 64}],
    "tags": [{"chunk_no": 1, "entity": "ApplicationOverview", "origin": "rule", "score": 4, "evidence": "heading 'introduction'"}],
}


def test_minimal_payload_is_valid_and_chunks_and_tags_default_to_empty():
    obj = SourceRecord.model_validate(MINIMAL)
    assert obj.chunks == [] and obj.tags == []


def test_full_payload_round_trips():
    obj = SourceRecord.model_validate(FULL)
    assert SourceRecord.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", list(MINIMAL))
def test_missing_mandatory_field_is_rejected(field):
    with pytest.raises(ValidationError) as caught:
        SourceRecord.model_validate({k: v for k, v in FULL.items() if k != field})
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SourceRecord.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field,value", [("path", ""), ("hashcode", "short"), ("version", 0), ("timestamp", "")])
def test_values_outside_the_constraints_are_rejected(field, value):
    with pytest.raises(ValidationError):
        SourceRecord.model_validate({**FULL, field: value})


def test_nested_chunks_and_tags_are_validated():
    with pytest.raises(ValidationError):
        SourceRecord.model_validate({**FULL, "chunks": [{"chunk_no": 0, "heading": "x", "text_hash": "1" * 64}]})
    with pytest.raises(ValidationError):
        SourceRecord.model_validate({**FULL, "tags": [{"chunk_no": 1, "entity": "", "origin": "rule"}]})


@pytest.mark.parametrize("field", list(MINIMAL) + ["chunks", "tags"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SourceRecord.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
