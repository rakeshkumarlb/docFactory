import pytest
from pydantic import ValidationError

from docfactory.entitymodels.items.kpi import Kpi
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "name": "Test KPI",
    "definition": "Test definition",
}

FULL = {
    "name": "Test KPI",
    "definition": "Test definition",
    "unit": "Test unit",
    "target": "Test target",
    "current_value": "Test current value",
    "measurement_frequency": "Test frequency",
    "owner": "Test owner",
    "data_source": "Test data source",
}


def test_minimal_payload_is_valid():
    Kpi.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Kpi.model_validate(FULL)
    assert Kpi.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["name", "definition"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        Kpi.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Kpi.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Kpi.model_validate(MINIMAL)
    assert obj.unit == ''
    assert obj.target == ''
    assert obj.current_value == ''
    assert obj.measurement_frequency == ''
    assert obj.owner == ''
    assert obj.data_source is None


@pytest.mark.parametrize("field", ["name", "definition"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        Kpi.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["data_source"])
def test_not_applicable_is_accepted_where_allowed(field):
    Kpi.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


@pytest.mark.parametrize("field", ["name", "definition", "unit", "target", "current_value", "measurement_frequency", "owner"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Kpi.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Kpi has 8 scored fields, 2 of them mandatory (name, definition).


def test_completeness_of_mandatory_only_payload():
    # answered 2 (mandatory) / total 8 -> 2 / 8 * 100
    obj = Kpi.model_validate(MINIMAL)
    assert field_counts(obj) == (2, 8)
    assert completeness(obj) == pytest.approx(2 / 8 * 100)


def test_completeness_of_fully_filled_payload_is_100():
    # all 8 fields differ from their defaults: 8 / 8 * 100
    obj = Kpi.model_validate(FULL)
    assert field_counts(obj) == (8, 8)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ('' / None) leave answered at 2 of 8
    payload = {
        **MINIMAL,
        "unit": "",
        "target": "",
        "current_value": "",
        "measurement_frequency": "",
        "owner": "",
        "data_source": None,
    }
    obj = Kpi.model_validate(payload)
    assert field_counts(obj) == (2, 8)


def test_legal_not_applicable_counts_as_answered():
    # 2 mandatory + data_source N/A = 3 answered / 8
    na = NotApplicable(reason="Not relevant for this test.")
    obj = Kpi.model_validate({**MINIMAL, "data_source": na})
    assert field_counts(obj) == (3, 8)
    assert completeness(obj) == pytest.approx(3 / 8 * 100)
