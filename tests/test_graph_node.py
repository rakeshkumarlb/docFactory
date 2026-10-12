import pytest
from pydantic import ValidationError

from docfactory.models.graph_node import GraphNode

MINIMAL = {"id": "/A/B.md", "type": "Requirement", "title": "FR-01"}
FULL = {"id": "/A/B.md", "type": "Requirement", "title": "FR-01", "identifier": "FR-01"}


def test_minimal_payload_is_valid():
    GraphNode.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = GraphNode.model_validate(FULL)
    assert GraphNode.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["id", "type", "title"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        GraphNode.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        GraphNode.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = GraphNode.model_validate(MINIMAL)
    assert obj.identifier == ""


def test_empty_text_is_rejected():
    for field in ("id", "type", "title"):
        with pytest.raises(ValidationError):
            GraphNode.model_validate({**FULL, field: ""})
