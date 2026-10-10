import pytest
from pydantic import ValidationError

from docfactory.completeness import completeness
from docfactory.documentmodels.document_body import DocumentBody

def test_empty_body_is_valid_and_not_complete():
    assert completeness(DocumentBody.model_validate({})) == 0


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        DocumentBody.model_validate({"sections": [], "x": 1})

