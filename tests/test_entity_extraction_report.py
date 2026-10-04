import pytest
from pydantic import ValidationError

from docfactory.models.entity_extraction_report import EntityExtractionReport
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.save_action import SaveAction
from docfactory.models.save_error import SaveError

MINIMAL = {
    "entity": "Test-Entity",
    "outcome": ExtractionOutcome.SAVED,
}

FULL = {
    "entity": "Test-Entity",
    "outcome": ExtractionOutcome.SAVED,
    "key": "Test.Key",
    "reason": "test reason",
    "chunks_used": 3,
    "batches": 2,
    "failed_batches": 1,
    "contributions": 2,
    "items": 4,
    "action": SaveAction.CREATED,
    "version": 2,
    "completeness": 62.5,
    "missing_questions": ["test question?"],
    "ungrounded_values": ["test value"],
    "conflicts": ["test conflict"],
    "batch_notes": ["test note"],
    "save_errors": [SaveError(path="a", message="m", error_type="t")],
}


def test_minimal_payload_is_valid():
    EntityExtractionReport.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = EntityExtractionReport.model_validate(FULL)
    assert EntityExtractionReport.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["entity", "outcome"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        EntityExtractionReport.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        EntityExtractionReport.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = EntityExtractionReport.model_validate(MINIMAL)
    assert obj.key is None
    assert obj.reason == ''
    assert obj.chunks_used == 0
    assert obj.batches == 0
    assert obj.failed_batches == 0
    assert obj.contributions == 0
    assert obj.items == 0
    assert obj.action is None
    assert obj.version is None
    assert obj.completeness is None
    assert obj.missing_questions == []
    assert obj.ungrounded_values == []
    assert obj.conflicts == []
    assert obj.batch_notes == []
    assert obj.save_errors == []


@pytest.mark.parametrize("field", ["entity"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        EntityExtractionReport.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["entity", "outcome", "key", "reason", "chunks_used", "batches", "failed_batches", "contributions", "items", "action", "version", "completeness", "missing_questions", "ungrounded_values", "conflicts", "batch_notes", "save_errors"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        EntityExtractionReport.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
