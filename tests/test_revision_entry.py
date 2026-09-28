import pytest
from pydantic import ValidationError

from docfactory.documentmodels.shared.revision_entry import RevisionEntry
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "version": "1.0",
    "date": "2024-01-15",
    "summary": "Initial draft created.",
}

FULL = {
    "version": "1.0",
    "date": "2024-01-15",
    "summary": "Initial draft created.",
    "author": "Jane Doe",
}


def test_minimal_payload_is_valid():
    RevisionEntry.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = RevisionEntry.model_validate(FULL)
    assert RevisionEntry.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["version", "date", "summary"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        RevisionEntry.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        RevisionEntry.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = RevisionEntry.model_validate(MINIMAL)
    assert obj.author == ''


@pytest.mark.parametrize("field", ["version", "date", "summary"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        RevisionEntry.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["version", "date", "summary", "author"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        RevisionEntry.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
