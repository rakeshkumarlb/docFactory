import pytest
from pydantic import ValidationError

from docfactory.models.relationship_graph import RelationshipGraph

MINIMAL = {"scope": "Acme"}
FULL = {"scope": "Acme", "nodes": [{"id": "/A.md", "type": "Fact", "title": "A"}], "edges": [{"source": "/A.md", "target": "/B.md", "kind": "part_of", "origin": "structural"}]}


def test_minimal_payload_is_valid():
    RelationshipGraph.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = RelationshipGraph.model_validate(FULL)
    assert RelationshipGraph.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["scope"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        RelationshipGraph.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        RelationshipGraph.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = RelationshipGraph.model_validate(MINIMAL)
    assert (obj.nodes, obj.edges) == ([], [])


def test_empty_scope_is_rejected():
    with pytest.raises(ValidationError):
        RelationshipGraph.model_validate({**FULL, "scope": ""})
