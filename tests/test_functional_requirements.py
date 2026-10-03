import pytest
from pydantic import ValidationError

from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.requirement import Requirement

MINIMAL = {}

FULL = {
    "summary": "Test summary",
    "requirements": [{"id": "FR-TEST", "title": "Test title", "description": "Test description"}],
    "out_of_scope": ["Test exclusion"],
}


def test_minimal_payload_is_valid():
    FunctionalRequirements.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FunctionalRequirements.model_validate(FULL)
    assert FunctionalRequirements.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FunctionalRequirements.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = FunctionalRequirements.model_validate(MINIMAL)
    assert obj.summary == ''
    assert obj.requirements == []
    assert obj.out_of_scope == []


@pytest.mark.parametrize("field", ["out_of_scope"])
def test_not_applicable_is_accepted_where_allowed(field):
    FunctionalRequirements.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["summary", "requirements"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FunctionalRequirements.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

FULL_ITEM = {"id": "FR-TEST", "title": "Test title", "description": "Test description", "priority": "MUST",
             "rationale": "Test rationale", "acceptance_criteria": ["Test criterion"]}
HALF_ITEM = {"id": "FR-TEST", "title": "Test title", "description": "Test description"}


def test_completeness_of_empty_payload():
    # 3 top-level fields, all at their defaults (an empty list is one unanswered field) -> 0 / 3
    obj = FunctionalRequirements.model_validate({})
    assert field_counts(obj) == (0, 3)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # summary 1 + requirements (one item of 6) + out_of_scope 1 = 8 / 8
    obj = FunctionalRequirements.model_validate(
        {"summary": "Test summary", "requirements": [FULL_ITEM], "out_of_scope": ["Test exclusion"]})
    assert field_counts(obj) == (8, 8)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    obj = FunctionalRequirements.model_validate({"summary": "", "requirements": [], "out_of_scope": []})
    assert field_counts(obj) == (0, 3)


def test_legal_not_applicable_on_out_of_scope_counts_as_answered():
    # out_of_scope N/A = 1 answered / 3
    obj = FunctionalRequirements.model_validate({"out_of_scope": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (1, 3)
    assert completeness(obj) == pytest.approx(1 / 3 * 100)


def test_two_item_list_scores_both_items_fields():
    # items: full 6/6 + mandatory-only 3/6 = 9/12; summary 0/1, out_of_scope 0/1 -> 9 / 14
    obj = FunctionalRequirements.model_validate({"requirements": [FULL_ITEM, HALF_ITEM]})
    assert field_counts(obj) == (9, 14)
    assert completeness(obj) == pytest.approx(9 / 14 * 100)
