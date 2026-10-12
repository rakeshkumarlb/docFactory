import pytest
from pydantic import ValidationError

from docfactory.entitymodels.items.relation import Relation
from docfactory.entitymodels.items.relation_kind import RelationKind

MINIMAL = {"target": "FR-03", "kind": RelationKind.DEPENDS_ON}
FULL = {"target": "FR-03", "kind": RelationKind.DEPENDS_ON, "evidence": "requires FR-03"}


def test_minimal_payload_is_valid():
    Relation.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Relation.model_validate(FULL)
    assert Relation.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["target", "kind"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        Relation.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Relation.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = Relation.model_validate(MINIMAL)
    assert obj.evidence == ""


def test_kind_must_be_a_known_kind_and_target_not_empty():
    with pytest.raises(ValidationError):
        Relation.model_validate({**FULL, "kind": "likes"})
    with pytest.raises(ValidationError):
        Relation.model_validate({**FULL, "target": ""})
    assert Relation.model_validate({**FULL, "kind": "implements"}).kind is RelationKind.IMPLEMENTS
