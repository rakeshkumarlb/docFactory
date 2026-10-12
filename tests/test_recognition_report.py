import pytest
from pydantic import ValidationError

from docfactory.models.recognition_report import RecognitionReport
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.recognition_outcome import RecognitionOutcome

MINIMAL = {
    "path": "Test/references/test.md",
    "outcome": RecognitionOutcome.RECOGNIZED,
}

FULL = {
    "path": "Test/references/test.md",
    "outcome": RecognitionOutcome.RECOGNIZED,
    "windows": 1,
    "calls": 1,
    "skipped_windows": 1,
    "failed_windows": 1,
    "entities": 1,
    "relations": 1,
    "notes": ["Test note"],
}


def test_minimal_payload_is_valid():
    RecognitionReport.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = RecognitionReport.model_validate(FULL)
    assert RecognitionReport.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["path", "outcome"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        RecognitionReport.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        RecognitionReport.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = RecognitionReport.model_validate(MINIMAL)
    assert obj.windows == 0
    assert obj.calls == 0
    assert obj.skipped_windows == 0
    assert obj.failed_windows == 0
    assert obj.entities == 0
    assert obj.relations == 0
    assert obj.notes == []


@pytest.mark.parametrize("field", ["path"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        RecognitionReport.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["path", "outcome", "windows", "calls", "skipped_windows", "failed_windows", "entities", "relations", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        RecognitionReport.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
