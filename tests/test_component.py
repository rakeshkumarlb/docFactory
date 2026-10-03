import pytest
from pydantic import ValidationError

from docfactory.entitymodels.items.component import Component
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "name": "Test name",
}

FULL = {
    "name": "Test name",
    "purpose": "Test purpose",
    "technology": "Test technology",
    "owner": "Test owner",
    "dependencies": ["Test dependencies"],
}


def test_minimal_payload_is_valid():
    Component.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Component.model_validate(FULL)
    assert Component.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["name"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        Component.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Component.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Component.model_validate(MINIMAL)
    assert obj.purpose == ''
    assert obj.technology == ''
    assert obj.owner == ''
    assert obj.dependencies == []


@pytest.mark.parametrize("field", ["name"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        Component.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["name", "purpose", "technology", "owner", "dependencies"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Component.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Component has 5 scored fields, 1 of them mandatory (name).


def test_completeness_of_mandatory_only_payload():
    # answered 1 (mandatory) / total 5 -> 1 / 5 * 100
    obj = Component.model_validate(MINIMAL)
    assert field_counts(obj) == (1, 5)
    assert completeness(obj) == pytest.approx(1 / 5 * 100)


def test_completeness_of_fully_filled_payload_is_100():
    # all 5 fields differ from their defaults: 5 / 5 * 100
    obj = Component.model_validate(FULL)
    assert field_counts(obj) == (5, 5)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 1 of 5
    defaults = {'purpose': '', 'technology': '', 'owner': '', 'dependencies': []}
    obj = Component.model_validate({**MINIMAL, **defaults})
    assert field_counts(obj) == (1, 5)
