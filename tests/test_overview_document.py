import pytest
from pydantic import ValidationError

from docfactory.documentmodels.overview_document import OverviewDocument
from docfactory.models.not_applicable import NotApplicable
from docfactory.documentmodels.application_summary_section import ApplicationSummarySection
from docfactory.documentmodels.kpi_summary_section import KpiSummarySection

MINIMAL = {
    "application_summary": {"application_name": "Test-App", "purpose": "Test purpose statement."},
    "kpi_summary": {"notes": "Test notes."},
}

FULL = {
    "application_summary": {"application_name": "Test-App", "purpose": "Test purpose statement."},
    "kpi_summary": {"notes": "Test notes."},
}


def test_minimal_payload_is_valid():
    OverviewDocument.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = OverviewDocument.model_validate(FULL)
    assert OverviewDocument.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["application_summary", "kpi_summary"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        OverviewDocument.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        OverviewDocument.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field", ["application_summary", "kpi_summary"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        OverviewDocument.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
