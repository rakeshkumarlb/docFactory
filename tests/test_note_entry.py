import pytest
from pydantic import ValidationError

from docfactory.entitymodels.items.note_entry import NoteEntry
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "title": "Test-Note",
}

FULL = {
    "title": "Test-Note",
    "summary": "Test summary.",
    "statements": ["Test statement."],
    "kind": "appendix",
    "source_chunks": ["Test/references/test.pdf#1"],
}


def test_minimal_payload_is_valid():
    NoteEntry.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = NoteEntry.model_validate(FULL)
    assert NoteEntry.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["title"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        NoteEntry.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        NoteEntry.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = NoteEntry.model_validate(MINIMAL)
    assert obj.summary == ''
    assert obj.statements == []
    assert obj.kind == ''
    assert obj.source_chunks == []


@pytest.mark.parametrize("field", ["title"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        NoteEntry.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["title", "summary", "statements", "kind", "source_chunks"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        NoteEntry.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
