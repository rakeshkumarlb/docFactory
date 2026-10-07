import pytest
from pydantic import ValidationError

from docfactory.models.fact_question import FactQuestion
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "path": "test_items[].test_field",
    "question": "Test question?",
    "default_assumed": "empty text",
}

FULL = {
    "path": "test_items[].test_field",
    "question": "Test question?",
    "default_assumed": "empty text",
    "missing_in": 2,
    "item_count": 3,
}


def test_minimal_payload_is_valid():
    FactQuestion.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FactQuestion.model_validate(FULL)
    assert FactQuestion.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["path", "question", "default_assumed"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        FactQuestion.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FactQuestion.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = FactQuestion.model_validate(MINIMAL)
    assert obj.missing_in is None
    assert obj.item_count is None


@pytest.mark.parametrize("field", ["path", "question", "default_assumed"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        FactQuestion.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["path", "question", "default_assumed", "missing_in", "item_count"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FactQuestion.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
