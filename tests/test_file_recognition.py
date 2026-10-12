import pytest
from pydantic import ValidationError

from docfactory.models.file_recognition import FileRecognition
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.window_recognition import WindowRecognition

MINIMAL = {
    "resource": "Test/references/test.md",
    "hashcode": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "generated_by": "test-agent/1",
    "timestamp": "2026-01-01T00:00:00+00:00",
}

FULL = {
    "resource": "Test/references/test.md",
    "windows": [],
    "hashcode": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "generated_by": "test-agent/1",
    "timestamp": "2026-01-01T00:00:00+00:00",
}


def test_minimal_payload_is_valid():
    FileRecognition.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FileRecognition.model_validate(FULL)
    assert FileRecognition.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["resource", "hashcode", "generated_by", "timestamp"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        FileRecognition.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FileRecognition.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = FileRecognition.model_validate(MINIMAL)
    assert obj.windows == []


@pytest.mark.parametrize("field", ["resource", "generated_by", "timestamp"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        FileRecognition.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["hashcode"])
def test_text_not_matching_the_pattern_is_rejected(field):
    with pytest.raises(ValidationError):
        FileRecognition.model_validate({**FULL, field: "not matching the pattern"})


@pytest.mark.parametrize("field", ["resource", "windows", "hashcode", "generated_by", "timestamp"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FileRecognition.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
