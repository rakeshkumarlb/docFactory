import pytest
from pydantic import ValidationError

from docfactory.models.entity_signals import EntitySignals
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "entity": "TestEntity",
}

FULL = {
    "entity": "TestEntity",
    "heading_terms": ["test heading"],
    "id_patterns": [r"\bTST-\d+"],
    "keywords": ["test keyword"],
}


def test_minimal_payload_is_valid():
    EntitySignals.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = EntitySignals.model_validate(FULL)
    assert EntitySignals.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["entity"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        EntitySignals.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        EntitySignals.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = EntitySignals.model_validate(MINIMAL)
    assert obj.heading_terms == []
    assert obj.id_patterns == []
    assert obj.keywords == []


@pytest.mark.parametrize("field", ["entity"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        EntitySignals.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["entity", "heading_terms", "id_patterns", "keywords"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        EntitySignals.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


def test_bad_regular_expression_is_rejected_and_named():
    with pytest.raises(ValidationError) as caught:
        EntitySignals.model_validate({**FULL, "id_patterns": [r"\bOK-\d+", "FR-(\d+"]})
    assert "FR-(" in str(caught.value)


def test_valid_regular_expressions_are_kept():
    obj = EntitySignals.model_validate(FULL)
    assert obj.id_patterns == [r"\bTST-\d+"]
