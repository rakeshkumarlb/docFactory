import pytest
from pydantic import ValidationError

from docfactory.models.generation_report import GenerationReport
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.save_action import SaveAction

MINIMAL = {
    "doc_type": "SRS",
    "body_key": "Test-App.Outputs.SRS",
}

FULL = {
    "doc_type": "SRS",
    "body_key": "Test-App.Outputs.SRS",
    "body_action": SaveAction.CREATED,
    "body_version": 2,
    "body_completeness": 50.0,
    "document_version": "0.1",
    "revision_added": "Test revision summary.",
    "gap_count": 3,
    "need_count": 2,
    "needs_origin": "no_llm",
    "needs_skipped": True,
    "needs_note": "Test note.",
    "output_files": ["output/Test-App/SRS.md"],
    "errors": ["Test error line."],
}


def test_minimal_payload_is_valid():
    GenerationReport.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = GenerationReport.model_validate(FULL)
    assert GenerationReport.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["doc_type", "body_key"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        GenerationReport.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        GenerationReport.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = GenerationReport.model_validate(MINIMAL)
    assert obj.body_action is None
    assert obj.body_version is None
    assert obj.body_completeness is None
    assert obj.document_version == ''
    assert obj.revision_added == ''
    assert obj.gap_count == 0
    assert obj.need_count == 0
    assert obj.needs_origin == ''
    assert obj.needs_skipped is False
    assert obj.needs_note == ''
    assert obj.output_files == []
    assert obj.errors == []


@pytest.mark.parametrize("field", ["doc_type", "body_key"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        GenerationReport.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["doc_type", "body_key", "body_action", "body_version", "body_completeness", "document_version", "revision_added", "gap_count", "need_count", "needs_origin", "needs_skipped", "needs_note", "output_files", "errors"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        GenerationReport.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
