import pytest
from pydantic import ValidationError

from docfactory.entitymodels.items.slo_objective import SloObjective
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "name": "Test name",
}

FULL = {
    "name": "Test name",
    "definition": "Test definition",
    "target": "Test target",
    "measurement_window": "Test measurement window",
    "measurement_source": "Test measurement source",
    "breach_consequence": "Test breach consequence",
}


def test_minimal_payload_is_valid():
    SloObjective.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = SloObjective.model_validate(FULL)
    assert SloObjective.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["name"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        SloObjective.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        SloObjective.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = SloObjective.model_validate(MINIMAL)
    assert obj.definition == ''
    assert obj.target == ''
    assert obj.measurement_window == ''
    assert obj.measurement_source == ''
    assert obj.breach_consequence == ''


@pytest.mark.parametrize("field", ["name"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        SloObjective.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["name", "definition", "target", "measurement_window", "measurement_source", "breach_consequence"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        SloObjective.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# SloObjective has 6 scored fields, 1 of them mandatory (name).


def test_completeness_of_mandatory_only_payload():
    # answered 1 (mandatory) / total 6 -> 1 / 6 * 100
    obj = SloObjective.model_validate(MINIMAL)
    assert field_counts(obj) == (1, 6)
    assert completeness(obj) == pytest.approx(1 / 6 * 100)


def test_completeness_of_fully_filled_payload_is_100():
    # all 6 fields differ from their defaults: 6 / 6 * 100
    obj = SloObjective.model_validate(FULL)
    assert field_counts(obj) == (6, 6)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / [] / None) leave answered at 1 of 6
    defaults = {'definition': '',
 'target': '',
 'measurement_window': '',
 'measurement_source': '',
 'breach_consequence': ''}
    obj = SloObjective.model_validate({**MINIMAL, **defaults})
    assert field_counts(obj) == (1, 6)
