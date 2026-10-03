import pytest
from pydantic import ValidationError

from docfactory.entitymodels.items.support_contact import SupportContact
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "role": "Test role",
}

FULL = {
    "role": "Test role",
    "team": "Test team",
    "contact_channel": "Test contact channel",
    "support_hours": "Test support hours",
    "escalates_to": "Test escalates to",
}


def test_minimal_payload_is_valid():
    SupportContact.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SupportContact.model_validate(FULL)
    assert SupportContact.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["role"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        SupportContact.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SupportContact.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = SupportContact.model_validate(MINIMAL)
    assert obj.team == ''
    assert obj.contact_channel == ''
    assert obj.support_hours == ''
    assert obj.escalates_to == ''


@pytest.mark.parametrize("field", ["role"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        SupportContact.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["role", "team", "contact_channel", "support_hours", "escalates_to"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SupportContact.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# SupportContact has 5 scored fields, 1 of them mandatory (role).


def test_completeness_of_mandatory_only_payload():
    # answered 1 (mandatory) / total 5 -> 1 / 5 * 100
    obj = SupportContact.model_validate(MINIMAL)
    assert field_counts(obj) == (1, 5)
    assert completeness(obj) == pytest.approx(1 / 5 * 100)


def test_completeness_of_fully_filled_payload_is_100():
    # all 5 fields differ from their defaults: 5 / 5 * 100
    obj = SupportContact.model_validate(FULL)
    assert field_counts(obj) == (5, 5)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 1 of 5
    defaults = {'team': '', 'contact_channel': '', 'support_hours': '', 'escalates_to': ''}
    obj = SupportContact.model_validate({**MINIMAL, **defaults})
    assert field_counts(obj) == (1, 5)
