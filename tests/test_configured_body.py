import pytest
from pydantic import ValidationError

from docfactory.completeness import completeness
from docfactory.models.configured_body import ConfiguredBody

def test_empty_body_is_valid_and_not_complete():
    assert completeness(ConfiguredBody.model_validate({})) == 0


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ConfiguredBody.model_validate({"sections": [], "x": 1})

