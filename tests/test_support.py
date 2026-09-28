import pytest
from pydantic import ValidationError

from docfactory.entitymodels.support import Support
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.support_contact import SupportContact

MINIMAL = {}

FULL = {
    "support_model": "Test support model",
    "contacts": [{"role": "Test support role"}],
    "escalation_path": "Test escalation path",
    "incident_process": "Test incident process",
    "runbooks": ["Test runbooks"],
}


def test_minimal_payload_is_valid():
    Support.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Support.model_validate(FULL)
    assert Support.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Support.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Support.model_validate(MINIMAL)
    assert obj.support_model == ''
    assert obj.contacts == []
    assert obj.escalation_path == ''
    assert obj.incident_process == ''
    assert obj.runbooks == []


@pytest.mark.parametrize("field", ["support_model", "contacts", "escalation_path", "incident_process", "runbooks"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Support.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Support has 5 top-level scored fields, none mandatory.
# Full payload total: support_model (1), contacts -> SupportContact item (5), escalation_path (1), incident_process (1), runbooks (1) = 9.
FULL_COMPLETE = {'support_model': 'Test support model',
 'contacts': [{'role': 'Test role',
               'team': 'Test team',
               'contact_channel': 'Test contact channel',
               'support_hours': 'Test support hours',
               'escalates_to': 'Test escalates to'}],
 'escalation_path': 'Test escalation path',
 'incident_process': 'Test incident process',
 'runbooks': ['Test runbooks']}


def test_completeness_of_mandatory_only_payload():
    # an empty payload: every one of the 5 top-level fields is at its default (an empty list counts as one unanswered field)
    # -> answered 0 / total 5
    obj = Support.model_validate(MINIMAL)
    assert field_counts(obj) == (0, 5)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # every field filled, each list holding one fully filled item -> 9 / 9 * 100
    obj = Support.model_validate(FULL_COMPLETE)
    assert field_counts(obj) == (9, 9)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 0 of 5
    defaults = {'support_model': '', 'contacts': [], 'escalation_path': '', 'incident_process': '', 'runbooks': []}
    obj = Support.model_validate(defaults)
    assert field_counts(obj) == (0, 5)


def test_two_item_list_scores_both_items_fields():
    # contacts: a fully filled item (5/5) and a mandatory-only item (1/5) -> 6/10;
    # the other 4 top-level fields stay at their defaults (0/1 each) -> overall 6 / 14
    full_item = {'role': 'Test role',
 'team': 'Test team',
 'contact_channel': 'Test contact channel',
 'support_hours': 'Test support hours',
 'escalates_to': 'Test escalates to'}
    half_item = {'role': 'Test role'}
    obj = Support.model_validate({"contacts": [full_item, half_item]})
    assert field_counts(obj) == (6, 14)
    assert completeness(obj) == pytest.approx(6 / 14 * 100)
