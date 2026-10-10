import pytest
from pydantic import ValidationError

from docfactory.completeness import completeness
from docfactory.models.configured_section import ConfiguredSection

FIELD = {"binding": "Sop.notes", "label": "Notes", "status": "answered", "value": '"x"'}


def test_section_completeness_is_the_share_of_answered_fields():
    section = ConfiguredSection.model_validate({"id": "sop", "title": "SOP", "fields": [FIELD, {**FIELD, "status": "missing", "value": ""}]})
    assert completeness(section) == 50


@pytest.mark.parametrize("bad", [{"id": "", "title": "T"}, {"id": "a"}, {"id": "a", "title": "T", "x": 1}])
def test_invalid_payloads_are_rejected(bad):
    with pytest.raises(ValidationError):
        ConfiguredSection.model_validate(bad)

