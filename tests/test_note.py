import pytest
from pydantic import ValidationError

from docfactory.entitymodels.facts.note import Note
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.note_entry import NoteEntry

MINIMAL = {}

FULL = {
    "overview": "Test overview.",
    "notes": [],
}


def test_minimal_payload_is_valid():
    Note.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Note.model_validate(FULL)
    assert Note.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Note.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Note.model_validate(MINIMAL)
    assert obj.overview == ''
    assert obj.notes == []


@pytest.mark.parametrize("field", ["overview", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Note.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
