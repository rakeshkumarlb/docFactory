import pytest
from pydantic import ValidationError

from docfactory.documentmodels.document_gap import DocumentGap
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "number": 1,
    "field": "application_summary.business_overview",
    "question": "What is the primary business purpose of this application?",
    "expected_source": "ApplicationOverview.business_overview",
}

FULL = {
    **MINIMAL,
    "number": 2,
    "field": "functional_requirements.requirements[].acceptance_criteria",
    "expected_source": "FunctionalRequirements.requirements[].acceptance_criteria",
    "missing_in": 2,
    "item_count": 5,
    "example_items": ["TEST-1 | Test item", "TEST-2 | Other test item"],
}

MANDATORY = ["number", "field", "question", "expected_source"]
TEXT = ["field", "question", "expected_source"]


def test_minimal_payload_is_valid_with_honest_defaults():
    gap = DocumentGap.model_validate(MINIMAL)
    assert gap.missing_in is None
    assert gap.item_count is None
    assert gap.example_items == []


def test_full_payload_round_trips():
    obj = DocumentGap.model_validate(FULL)
    assert DocumentGap.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", MANDATORY)
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        DocumentGap.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_wrong_type_is_rejected():
    with pytest.raises(ValidationError):
        DocumentGap.model_validate({**FULL, "number": "one"})
    with pytest.raises(ValidationError):
        DocumentGap.model_validate({**FULL, "example_items": "not a list"})


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        DocumentGap.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field", TEXT)
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        DocumentGap.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("number", [0, -1])
def test_number_below_one_is_rejected(number):
    with pytest.raises(ValidationError):
        DocumentGap.model_validate({**FULL, "number": number})


def test_at_most_three_example_items():
    DocumentGap.model_validate({**FULL, "example_items": ["a", "b", "c"]})
    with pytest.raises(ValidationError):
        DocumentGap.model_validate({**FULL, "example_items": ["a", "b", "c", "d"]})


@pytest.mark.parametrize("field", MANDATORY + ["missing_in", "item_count", "example_items"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        DocumentGap.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
