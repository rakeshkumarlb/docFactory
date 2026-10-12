import pytest
from pydantic import ValidationError

from docfactory.models.coverage_report import CoverageReport

MINIMAL = {"path": "Test/references/test.pdf"}
FULL = {"path": "Test/references/test.pdf", "chunks": [{"chunk_no": 1, "heading": "H", "status": "UNMAPPED"}]}


def test_minimal_payload_is_valid():
    CoverageReport.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = CoverageReport.model_validate(FULL)
    assert CoverageReport.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["path"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        CoverageReport.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        CoverageReport.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = CoverageReport.model_validate(MINIMAL)
    assert obj.chunks == []


def test_empty_path_is_rejected():
    with pytest.raises(ValidationError):
        CoverageReport.model_validate({**FULL, "path": ""})
