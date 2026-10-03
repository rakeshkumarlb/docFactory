import pytest
from pydantic import ValidationError

from docfactory.entitymodels.facts.sop import Sop
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.sop_procedure import SopProcedure

MINIMAL = {}

FULL = {
    "procedures": [{"name": "Test procedure"}],
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    Sop.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Sop.model_validate(FULL)
    assert Sop.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Sop.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Sop.model_validate(MINIMAL)
    assert obj.procedures == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["procedures", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Sop.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Sop has 2 top-level scored fields, none mandatory.
# Full payload total: procedures -> SopProcedure item (9), notes (1) = 10.
FULL_COMPLETE = {'procedures': [{'name': 'Test name',
                 'purpose': 'Test purpose',
                 'trigger': 'Test trigger',
                 'frequency': 'Test frequency',
                 'roles': ['Test roles'],
                 'prerequisites': ['Test prerequisites'],
                 'steps': ['Test steps'],
                 'verification': 'Test verification',
                 'escalation': 'Test escalation'}],
 'notes': 'Test notes'}


def test_completeness_of_mandatory_only_payload():
    # an empty payload: every one of the 2 top-level fields is at its default (an empty list counts as one unanswered field)
    # -> answered 0 / total 2
    obj = Sop.model_validate(MINIMAL)
    assert field_counts(obj) == (0, 2)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # every field filled, each list holding one fully filled item -> 10 / 10 * 100
    obj = Sop.model_validate(FULL_COMPLETE)
    assert field_counts(obj) == (10, 10)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 0 of 2
    defaults = {'procedures': [], 'notes': ''}
    obj = Sop.model_validate(defaults)
    assert field_counts(obj) == (0, 2)


def test_two_item_list_scores_both_items_fields():
    # procedures: a fully filled item (9/9) and a mandatory-only item (1/9) -> 10/18;
    # the other 1 top-level fields stay at their defaults (0/1 each) -> overall 10 / 19
    full_item = {'name': 'Test name',
 'purpose': 'Test purpose',
 'trigger': 'Test trigger',
 'frequency': 'Test frequency',
 'roles': ['Test roles'],
 'prerequisites': ['Test prerequisites'],
 'steps': ['Test steps'],
 'verification': 'Test verification',
 'escalation': 'Test escalation'}
    half_item = {'name': 'Test name'}
    obj = Sop.model_validate({"procedures": [full_item, half_item]})
    assert field_counts(obj) == (10, 19)
    assert completeness(obj) == pytest.approx(10 / 19 * 100)
