import pytest
from pydantic import ValidationError

from docfactory.models.ingest_report import IngestReport
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.ingest_outcome import IngestOutcome

MINIMAL = {
    "file_name": "test-file.txt",
    "outcome": IngestOutcome.NEW,
}

FULL = {
    "file_name": "test-file.txt",
    "outcome": IngestOutcome.NEW,
    "target_path": "Test-Scope/test-file.txt",
    "version": 3,
    "chunk_count": 7,
    "entity_summary": ["Test-Entity: 2 chunks"],
    "unmapped_chunks": [1, 2],
    "changed_entities": ["Test-Entity"],
    "reason": "test reason",
}


def test_minimal_payload_is_valid():
    IngestReport.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = IngestReport.model_validate(FULL)
    assert IngestReport.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["file_name", "outcome"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        IngestReport.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        IngestReport.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = IngestReport.model_validate(MINIMAL)
    assert obj.target_path is None
    assert obj.version is None
    assert obj.chunk_count == 0
    assert obj.entity_summary == []
    assert obj.unmapped_chunks == []
    assert obj.changed_entities == []
    assert obj.reason == ''


@pytest.mark.parametrize("field", ["file_name"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        IngestReport.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["file_name", "outcome", "target_path", "version", "chunk_count", "entity_summary", "unmapped_chunks", "changed_entities", "reason"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        IngestReport.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
