import pytest
from pydantic import ValidationError

from docfactory.models.note_draft import NoteDraft

MINIMAL = {"title": "Test-Note", "chunks": [1]}
FULL = {"title": "Test-Note", "summary": "s", "statements": ["x"], "kind": "appendix", "chunks": [1, 2]}


def test_minimal_payload_is_valid():
    NoteDraft.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = NoteDraft.model_validate(FULL)
    assert NoteDraft.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["title", "chunks"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        NoteDraft.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        NoteDraft.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = NoteDraft.model_validate(MINIMAL)
    assert (obj.summary, obj.statements, obj.kind) == ("", [], "")


def test_a_note_needs_a_title_and_at_least_one_chunk():
    for bad in ({"title": ""}, {"chunks": []}):
        with pytest.raises(ValidationError):
            NoteDraft.model_validate({**FULL, **bad})
