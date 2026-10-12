import pytest
from pydantic import ValidationError

from docfactory.models.entity_link import EntityLink
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "target": "Component/test-target",
    "relation": "depends on",
}

FULL = {
    "target": "Component/test-target",
    "relation": "depends on",
    "kind": "depends_on",
    "resources": ["Test/references/test.md"],
}


def test_minimal_payload_is_valid():
    EntityLink.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = EntityLink.model_validate(FULL)
    assert EntityLink.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["target", "relation"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        EntityLink.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        EntityLink.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = EntityLink.model_validate(MINIMAL)
    assert obj.kind == ''
    assert obj.resources == []


@pytest.mark.parametrize("field", ["target", "relation"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        EntityLink.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["target", "relation", "kind", "resources"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        EntityLink.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
