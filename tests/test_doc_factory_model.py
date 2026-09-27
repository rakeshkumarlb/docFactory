import pytest
from pydantic import ValidationError

from docfactory.models.doc_factory_model import DocFactoryModel


class _Sample(DocFactoryModel):
    """Test-only model."""

    name: str


def test_valid_payload_is_accepted():
    assert _Sample.model_validate({"name": "x"}).name == "x"


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError) as caught:
        _Sample.model_validate({"name": "x", "surprise": 1})
    assert caught.value.errors()[0]["type"] == "extra_forbidden"
