import pytest
from pydantic import ValidationError

from docfactory.entitymodels.facts.environments import Environments
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.environment import Environment

MINIMAL = {}

FULL = {
    "environments": [{"name": "Test environment"}],
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    Environments.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Environments.model_validate(FULL)
    assert Environments.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Environments.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Environments.model_validate(MINIMAL)
    assert obj.environments == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["environments", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Environments.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Environments has 2 top-level scored fields, none mandatory.
# Full payload total: environments -> Environment item (6), notes (1) = 7.
FULL_COMPLETE = {'environments': [{'name': 'Test name',
                   'purpose': 'Test purpose',
                   'hosting': 'Test hosting',
                   'url': 'Test url',
                   'access_control': 'Test access control',
                   'notes': 'Test notes'}],
 'notes': 'Test notes'}


def test_completeness_of_mandatory_only_payload():
    # an empty payload: every one of the 2 top-level fields is at its default (an empty list counts as one unanswered field)
    # -> answered 0 / total 2
    obj = Environments.model_validate(MINIMAL)
    assert field_counts(obj) == (0, 2)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # every field filled, each list holding one fully filled item -> 7 / 7 * 100
    obj = Environments.model_validate(FULL_COMPLETE)
    assert field_counts(obj) == (7, 7)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 0 of 2
    defaults = {'environments': [], 'notes': ''}
    obj = Environments.model_validate(defaults)
    assert field_counts(obj) == (0, 2)


def test_two_item_list_scores_both_items_fields():
    # environments: a fully filled item (6/6) and a mandatory-only item (1/6) -> 7/12;
    # the other 1 top-level fields stay at their defaults (0/1 each) -> overall 7 / 13
    full_item = {'name': 'Test name',
 'purpose': 'Test purpose',
 'hosting': 'Test hosting',
 'url': 'Test url',
 'access_control': 'Test access control',
 'notes': 'Test notes'}
    half_item = {'name': 'Test name'}
    obj = Environments.model_validate({"environments": [full_item, half_item]})
    assert field_counts(obj) == (7, 13)
    assert completeness(obj) == pytest.approx(7 / 13 * 100)
