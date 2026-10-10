import pytest
from pydantic import ValidationError

from docfactory.completeness import completeness
from docfactory.models.document_field import DocumentField

MINIMAL = {"binding": "Sop.notes", "label": "Notes"}


def test_defaults_are_a_missing_field_with_no_value():
    obj = DocumentField.model_validate(MINIMAL)
    assert (obj.status, obj.value, obj.render_as) == ("missing", "", "list")


def test_only_the_value_is_scored():
    assert completeness(DocumentField.model_validate(MINIMAL)) == 0
    assert completeness(DocumentField.model_validate({**MINIMAL, "status": "answered", "value": '"x"'})) == 100


@pytest.mark.parametrize("bad", [{"binding": "Sop.notes"}, {**MINIMAL, "status": "maybe"}, {**MINIMAL, "render_as": "grid"}, {**MINIMAL, "x": 1}])
def test_invalid_payloads_are_rejected(bad):
    with pytest.raises(ValidationError):
        DocumentField.model_validate(bad)

