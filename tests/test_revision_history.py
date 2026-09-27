import pytest
from pydantic import ValidationError

from docfactory.documentmodels.revision_history import RevisionHistory
from docfactory.models.not_applicable import NotApplicable
from docfactory.documentmodels.revision_entry import RevisionEntry

MINIMAL = {}

FULL = {
    "revisions": [{"version": "1.0", "date": "2024-01-15", "summary": "Initial draft created.", "author": "Jane Doe"}],
    "notes": "Reviewed after each release.",
}


def test_minimal_payload_is_valid():
    RevisionHistory.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = RevisionHistory.model_validate(FULL)
    assert RevisionHistory.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        RevisionHistory.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = RevisionHistory.model_validate(MINIMAL)
    assert obj.revisions == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["revisions", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        RevisionHistory.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
