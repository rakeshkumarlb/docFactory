import pytest
from pydantic import ValidationError

from docfactory.entitymodels.kpis import Kpis
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.kpi import Kpi

MINIMAL = {}

FULL = {
    "kpis": [{"name": "Test KPI", "definition": "Test definition"}],
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    Kpis.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = Kpis.model_validate(FULL)
    assert Kpis.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        Kpis.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = Kpis.model_validate(MINIMAL)
    assert obj.kpis == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["kpis", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        Kpis.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


# --- Completeness (hand-written) ---
from docfactory.completeness import completeness, field_counts  # noqa: E402

# Kpis has 2 top-level scored fields (kpis, notes), neither mandatory. "kpis" is a list of Kpi
# items, so its own contribution is scored recursively over the items present (Kpi has 8 scored
# fields, 2 of them mandatory: name, definition). Neither top-level field allows NotApplicable, so
# that case is exercised on the Kpi item itself (tests/test_kpi.py) and generically in
# tests/test_completeness.py.

FULL_KPI = {
    "name": "Test KPI",
    "definition": "Test definition",
    "unit": "Test unit",
    "target": "Test target",
    "current_value": "Test current value",
    "measurement_frequency": "Test frequency",
    "owner": "Test owner",
    "data_source": "Test data source",
}
HALF_KPI = {"name": "Test KPI 2", "definition": "Test definition 2"}


def test_completeness_of_mandatory_only_payload():
    # an empty payload: empty "kpis" list is one unanswered field, "notes" at its default is
    # one unanswered field -> answered 0 / total 2
    obj = Kpis.model_validate(MINIMAL)
    assert field_counts(obj) == (0, 2)
    assert completeness(obj) == pytest.approx(0.0)


def test_completeness_of_fully_filled_payload_is_100():
    # one fully filled Kpi item (8/8) plus a filled "notes" (1/1) -> 9 / 9 * 100
    obj = Kpis.model_validate({"kpis": [FULL_KPI], "notes": "Test notes"})
    assert field_counts(obj) == (9, 9)
    assert completeness(obj) == pytest.approx(100.0)


def test_optional_fields_passed_as_their_default_are_not_counted():
    # explicit defaults ([] / '') leave answered at 0 of 2
    obj = Kpis.model_validate({"kpis": [], "notes": ""})
    assert field_counts(obj) == (0, 2)


def test_two_item_list_scores_both_items_fields():
    # a fully filled item (8/8) and a mandatory-only item (2/8) -> kpis contributes 10/16;
    # notes stays at its default (0/1) -> overall 10 / 17
    obj = Kpis.model_validate({"kpis": [FULL_KPI, HALF_KPI]})
    assert field_counts(obj) == (10, 17)
    assert completeness(obj) == pytest.approx(10 / 17 * 100)
