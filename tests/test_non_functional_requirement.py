import pytest
from pydantic import ValidationError

from docfactory.entitymodels.items.non_functional_requirement import NonFunctionalRequirement
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.non_functional_category import NonFunctionalCategory
from docfactory.entitymodels.items.requirement_priority import RequirementPriority

MINIMAL = {
    "id": "NFR-TEST",
    "category": "OTHER",
    "statement": "Test statement",
}

FULL = {
    "id": "NFR-TEST",
    "category": "OTHER",
    "statement": "Test statement",
    "target": "Test target",
    "priority": "SHOULD",
    "verification": "Test verification",
}


def test_minimal_payload_is_valid():
    NonFunctionalRequirement.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = NonFunctionalRequirement.model_validate(FULL)
    assert NonFunctionalRequirement.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["id", "category", "statement"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        NonFunctionalRequirement.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        NonFunctionalRequirement.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = NonFunctionalRequirement.model_validate(MINIMAL)
    assert obj.target is None
    assert obj.priority is None
    assert obj.verification is None


@pytest.mark.parametrize("field", ["id", "statement"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        NonFunctionalRequirement.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["target", "verification"])
def test_not_applicable_is_accepted_where_allowed(field):
    NonFunctionalRequirement.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["id", "category", "statement", "priority"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        NonFunctionalRequirement.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402


def test_completeness_of_mandatory_only_payload():
    # 3 mandatory answered / 6 total fields
    obj = NonFunctionalRequirement.model_validate(MINIMAL)
    assert field_counts(obj) == (3, 6)
    assert completeness(obj) == pytest.approx(50.0)


def test_completeness_of_fully_filled_payload_is_100():
    # all 6 fields answered: 6 / 6 * 100
    obj = NonFunctionalRequirement.model_validate(FULL)
    assert field_counts(obj) == (6, 6)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults (None) leave answered at 3 of 6
    obj = NonFunctionalRequirement.model_validate({**MINIMAL, "target": None, "priority": None, "verification": None})
    assert field_counts(obj) == (3, 6)


@pytest.mark.parametrize("field", ["target", "verification"])
def test_legal_not_applicable_counts_as_answered(field):
    # 3 mandatory + one N/A = 4 answered / 6
    obj = NonFunctionalRequirement.model_validate({**MINIMAL, field: NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (4, 6)
    assert completeness(obj) == pytest.approx(4 / 6 * 100)


def test_category_rejects_unknown_value():
    with pytest.raises(ValidationError):
        NonFunctionalRequirement.model_validate({**MINIMAL, "category": "SPEED"})
