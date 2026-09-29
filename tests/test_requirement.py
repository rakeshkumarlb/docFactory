import pytest
from pydantic import ValidationError

from docfactory.entitymodels.items.requirement import Requirement
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.requirement_priority import RequirementPriority

MINIMAL = {
    "id": "FR-TEST",
    "title": "Test title",
    "description": "Test description",
}

FULL = {
    "id": "FR-TEST",
    "title": "Test title",
    "description": "Test description",
    "priority": "MUST",
    "rationale": "Test rationale",
    "acceptance_criteria": ["Test criterion"],
}


def test_minimal_payload_is_valid():
    Requirement.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Requirement.model_validate(FULL)
    assert Requirement.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["id", "title", "description"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        Requirement.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Requirement.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Requirement.model_validate(MINIMAL)
    assert obj.priority is None
    assert obj.rationale is None
    assert obj.acceptance_criteria == []


@pytest.mark.parametrize("field", ["id", "title", "description"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        Requirement.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["rationale"])
def test_not_applicable_is_accepted_where_allowed(field):
    Requirement.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["id", "title", "description", "priority", "acceptance_criteria"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Requirement.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402


def test_completeness_of_mandatory_only_payload():
    # 3 mandatory answered / 6 total fields
    obj = Requirement.model_validate(MINIMAL)
    assert field_counts(obj) == (3, 6)
    assert completeness(obj) == pytest.approx(50.0)


def test_completeness_of_fully_filled_payload_is_100():
    # all 6 fields answered: 6 / 6 * 100
    obj = Requirement.model_validate(FULL)
    assert field_counts(obj) == (6, 6)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults (None / []) leave answered at 3 of 6
    obj = Requirement.model_validate({**MINIMAL, "priority": None, "rationale": None, "acceptance_criteria": []})
    assert field_counts(obj) == (3, 6)


def test_legal_not_applicable_on_rationale_counts_as_answered():
    # 3 mandatory + rationale N/A = 4 answered / 6
    obj = Requirement.model_validate({**MINIMAL, "rationale": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (4, 6)
    assert completeness(obj) == pytest.approx(4 / 6 * 100)


def test_priority_accepts_only_moscow_values():
    assert Requirement.model_validate({**MINIMAL, "priority": "WONT"}).priority == "WONT"
    with pytest.raises(ValidationError):
        Requirement.model_validate({**MINIMAL, "priority": "MAYBE"})
