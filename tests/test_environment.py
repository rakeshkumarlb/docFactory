import pytest
from pydantic import ValidationError

from docfactory.entitymodels.items.environment import Environment
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "name": "Test name",
}

FULL = {
    "name": "Test name",
    "purpose": "Test purpose",
    "hosting": "Test hosting",
    "url": "Test url",
    "access_control": "Test access control",
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    Environment.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Environment.model_validate(FULL)
    assert Environment.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["name"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        Environment.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Environment.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Environment.model_validate(MINIMAL)
    assert obj.purpose == ''
    assert obj.hosting == ''
    assert obj.url is None
    assert obj.access_control == ''
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["name"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        Environment.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["url"])
def test_not_applicable_is_accepted_where_allowed(field):
    Environment.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["name", "purpose", "hosting", "access_control", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Environment.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Environment has 6 scored fields, 1 of them mandatory (name).


def test_completeness_of_mandatory_only_payload():
    # answered 1 (mandatory) / total 6 -> 1 / 6 * 100
    obj = Environment.model_validate(MINIMAL)
    assert field_counts(obj) == (1, 6)
    assert completeness(obj) == pytest.approx(1 / 6 * 100)


def test_completeness_of_fully_filled_payload_is_100():
    # all 6 fields differ from their defaults: 6 / 6 * 100
    obj = Environment.model_validate(FULL)
    assert field_counts(obj) == (6, 6)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 1 of 6
    defaults = {'purpose': '', 'hosting': '', 'url': None, 'access_control': '', 'notes': ''}
    obj = Environment.model_validate({**MINIMAL, **defaults})
    assert field_counts(obj) == (1, 6)


def test_legal_not_applicable_on_url_counts_as_answered():
    # 1 mandatory + url N/A = 2 answered / 6
    obj = Environment.model_validate({**MINIMAL, "url": NotApplicable(reason="Not relevant for this test.")})
    assert field_counts(obj) == (2, 6)
    assert completeness(obj) == pytest.approx(2 / 6 * 100)
