import pytest
from pydantic import ValidationError

from docfactory.completeness import completeness
from docfactory.models.template_field import TemplateField

MINIMAL = {"binding": "Sop.notes"}


def test_minimal_payload_is_valid_with_defaults():
    obj = TemplateField.model_validate(MINIMAL)
    assert (obj.label, obj.render_as, obj.question) == ("", "list", "")


@pytest.mark.parametrize("bad", [{"binding": "nodot"}, {"binding": "Sop.Notes"}, {"binding": "Sop.notes", "render_as": "grid"}, {"binding": "Sop.notes", "x": 1}, {}])
def test_invalid_payloads_are_rejected(bad):
    with pytest.raises(ValidationError):
        TemplateField.model_validate(bad)

