import pytest
from pydantic import ValidationError

from docfactory.completeness import completeness
from docfactory.models.document_template import DocumentTemplate

SECTION = {"id": "sop", "title": "SOP", "fields": [{"binding": "Sop.notes"}]}
MINIMAL = {"doc_type": "SOP", "name": "Standard Operating Procedures", "sections": [SECTION]}


def test_minimal_payload_is_valid_and_round_trips():
    obj = DocumentTemplate.model_validate(MINIMAL)
    assert DocumentTemplate.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("bad", [{**MINIMAL, "doc_type": "has space"}, {**MINIMAL, "name": ""}, {**MINIMAL, "sections": []}, {"doc_type": "A"}, {**MINIMAL, "x": 1}])
def test_invalid_payloads_are_rejected(bad):
    with pytest.raises(ValidationError):
        DocumentTemplate.model_validate(bad)

