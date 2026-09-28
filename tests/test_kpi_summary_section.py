import pytest
from pydantic import ValidationError

from docfactory.documentmodels.entitybound.kpi_summary_section import KpiSummarySection
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.kpi import Kpi

MINIMAL = {}

FULL = {
    "kpis": [Kpi(name="Test KPI", definition="Test definition.")],
    "notes": "Test notes",
}


def test_minimal_payload_is_valid():
    KpiSummarySection.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = KpiSummarySection.model_validate(FULL)
    assert KpiSummarySection.model_validate(obj.model_dump()) == obj


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        KpiSummarySection.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = KpiSummarySection.model_validate(MINIMAL)
    assert obj.kpis == []
    assert obj.notes == ''


@pytest.mark.parametrize("field", ["kpis", "notes"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        KpiSummarySection.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
