import pytest
from pydantic import ValidationError

from docfactory.entitymodels.facts.non_functional_requirements import NonFunctionalRequirements
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.non_functional_requirement import NonFunctionalRequirement

MINIMAL = {}

FULL = {
    "summary": "Test summary",
    "requirements": [{"id": "NFR-TEST", "category": "OTHER", "statement": "Test statement"}],
}


def test_minimal_payload_is_valid():
    NonFunctionalRequirements.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = NonFunctionalRequirements.model_validate(FULL)
    assert NonFunctionalRequirements.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        NonFunctionalRequirements.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = NonFunctionalRequirements.model_validate(MINIMAL)
    assert obj.summary == ''
    assert obj.requirements == []


@pytest.mark.parametrize("field", ["summary", "requirements"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        NonFunctionalRequirements.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

FULL_ITEM = {"id": "NFR-TEST", "category": "OTHER", "statement": "Test statement", "target": "Test target",
             "priority": "SHOULD", "verification": "Test verification"}
HALF_ITEM = {"id": "NFR-TEST", "category": "OTHER", "statement": "Test statement"}


def test_completeness_of_empty_payload():
    # 2 top-level fields at their defaults -> 0 / 2
    obj = NonFunctionalRequirements.model_validate({})
    assert field_counts(obj) == (0, 2)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # summary 1 + requirements (one item of 6) = 7 / 7
    obj = NonFunctionalRequirements.model_validate({"summary": "Test summary", "requirements": [FULL_ITEM]})
    assert field_counts(obj) == (7, 7)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    obj = NonFunctionalRequirements.model_validate({"summary": "", "requirements": []})
    assert field_counts(obj) == (0, 2)


def test_two_item_list_scores_both_items_fields():
    # items: full 6/6 + mandatory-only 3/6 = 9/12; summary 0/1 -> 9 / 13
    obj = NonFunctionalRequirements.model_validate({"requirements": [FULL_ITEM, HALF_ITEM]})
    assert field_counts(obj) == (9, 13)
    assert completeness(obj) == pytest.approx(9 / 13 * 100)
