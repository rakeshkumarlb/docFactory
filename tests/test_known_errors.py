import pytest
from pydantic import ValidationError

from docfactory.entitymodels.facts.known_errors import KnownErrors
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.known_error import KnownError

MINIMAL = {}

FULL = {
    "known_errors": [{"title": "Test known error"}],
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    KnownErrors.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = KnownErrors.model_validate(FULL)
    assert KnownErrors.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        KnownErrors.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = KnownErrors.model_validate(MINIMAL)
    assert obj.known_errors == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["known_errors", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        KnownErrors.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# KnownErrors has 2 top-level scored fields, none mandatory.
# Full payload total: known_errors -> KnownError item (9), notes (1) = 10.
FULL_COMPLETE = {'known_errors': [{'title': 'Test title',
                   'error_id': 'Test error id',
                   'symptoms': 'Test symptoms',
                   'cause': 'Test cause',
                   'workaround': 'Test workaround',
                   'permanent_fix': 'Test permanent fix',
                   'severity': 'Test severity',
                   'status': 'Test status',
                   'related_ticket': 'Test related ticket'}],
 'notes': 'Test notes'}


def test_completeness_of_mandatory_only_payload():
    # an empty payload: every one of the 2 top-level fields is at its default (an empty list counts as one unanswered field)
    # -> answered 0 / total 2
    obj = KnownErrors.model_validate(MINIMAL)
    assert field_counts(obj) == (0, 2)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # every field filled, each list holding one fully filled item -> 10 / 10 * 100
    obj = KnownErrors.model_validate(FULL_COMPLETE)
    assert field_counts(obj) == (10, 10)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 0 of 2
    defaults = {'known_errors': [], 'notes': ''}
    obj = KnownErrors.model_validate(defaults)
    assert field_counts(obj) == (0, 2)


def test_two_item_list_scores_both_items_fields():
    # known_errors: a fully filled item (9/9) and a mandatory-only item (1/9) -> 10/18;
    # the other 1 top-level fields stay at their defaults (0/1 each) -> overall 10 / 19
    full_item = {'title': 'Test title',
 'error_id': 'Test error id',
 'symptoms': 'Test symptoms',
 'cause': 'Test cause',
 'workaround': 'Test workaround',
 'permanent_fix': 'Test permanent fix',
 'severity': 'Test severity',
 'status': 'Test status',
 'related_ticket': 'Test related ticket'}
    half_item = {'title': 'Test title'}
    obj = KnownErrors.model_validate({"known_errors": [full_item, half_item]})
    assert field_counts(obj) == (10, 19)
    assert completeness(obj) == pytest.approx(10 / 19 * 100)
