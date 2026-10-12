import pytest
from pydantic import ValidationError

from docfactory.models.graph_edge import GraphEdge

MINIMAL = {"source": "/A/B.md", "target": "/A/C.md", "kind": "part_of", "origin": "structural"}
FULL = {"source": "/A/B.md", "target": "/A/C.md", "kind": "depends_on", "origin": "stated", "evidence": "needs it", "resolved": False}


def test_minimal_payload_is_valid():
    GraphEdge.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = GraphEdge.model_validate(FULL)
    assert GraphEdge.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["source", "target", "kind", "origin"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        GraphEdge.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        GraphEdge.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = GraphEdge.model_validate(MINIMAL)
    assert (obj.evidence, obj.resolved) == ("", True)


def test_origin_is_one_of_three():
    for good in ("structural", "mentioned", "stated"):
        GraphEdge.model_validate({**FULL, "origin": good})
    with pytest.raises(ValidationError):
        GraphEdge.model_validate({**FULL, "origin": "guessed"})
