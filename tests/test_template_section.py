import pytest
from pydantic import ValidationError

from docfactory.completeness import completeness
from docfactory.models.template_section import TemplateSection

FIELD = {"binding": "Sop.notes"}
MINIMAL = {"id": "sop", "title": "SOP", "fields": [FIELD]}


def test_minimal_payload_is_valid_and_round_trips():
    obj = TemplateSection.model_validate(MINIMAL)
    assert TemplateSection.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("bad", [{**MINIMAL, "id": "Not Snake"}, {**MINIMAL, "title": ""}, {**MINIMAL, "fields": []}, {"id": "a", "title": "A"}, {**MINIMAL, "x": 1}])
def test_invalid_payloads_are_rejected(bad):
    with pytest.raises(ValidationError):
        TemplateSection.model_validate(bad)

