import pytest
from pydantic import ValidationError

from docfactory.models.data_store import DataStore
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "name": "Test name",
}

FULL = {
    "name": "Test name",
    "store_type": "Test store type",
    "technology": "Test technology",
    "contents": "Test contents",
}


def test_minimal_payload_is_valid():
    DataStore.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = DataStore.model_validate(FULL)
    assert DataStore.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["name"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        DataStore.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        DataStore.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = DataStore.model_validate(MINIMAL)
    assert obj.store_type == ''
    assert obj.technology == ''
    assert obj.contents == ''


@pytest.mark.parametrize("field", ["name"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        DataStore.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["name", "store_type", "technology", "contents"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        DataStore.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# DataStore has 4 scored fields, 1 of them mandatory (name).


def test_completeness_of_mandatory_only_payload():
    # answered 1 (mandatory) / total 4 -> 1 / 4 * 100
    obj = DataStore.model_validate(MINIMAL)
    assert field_counts(obj) == (1, 4)
    assert completeness(obj) == pytest.approx(1 / 4 * 100)


def test_completeness_of_fully_filled_payload_is_100():
    # all 4 fields differ from their defaults: 4 / 4 * 100
    obj = DataStore.model_validate(FULL)
    assert field_counts(obj) == (4, 4)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 1 of 4
    defaults = {'store_type': '', 'technology': '', 'contents': ''}
    obj = DataStore.model_validate({**MINIMAL, **defaults})
    assert field_counts(obj) == (1, 4)
