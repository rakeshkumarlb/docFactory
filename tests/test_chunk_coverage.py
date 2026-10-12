import pytest
from pydantic import ValidationError

from docfactory.models.chunk_coverage import ChunkCoverage
from docfactory.models.coverage_status import CoverageStatus

MINIMAL = {"chunk_no": 1, "heading": "H", "status": CoverageStatus.UNMAPPED}
FULL = {"chunk_no": 2, "heading": "H", "chars": 10, "status": CoverageStatus.NOTED, "entities": ["Test-Entity"], "reason": "r"}


def test_minimal_payload_is_valid():
    ChunkCoverage.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ChunkCoverage.model_validate(FULL)
    assert ChunkCoverage.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["chunk_no", "heading", "status"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ChunkCoverage.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ChunkCoverage.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = ChunkCoverage.model_validate(MINIMAL)
    assert (obj.chars, obj.entities, obj.reason) == (0, [], "")


def test_chunk_numbers_and_sizes_have_bounds():
    for bad in ({"chunk_no": 0}, {"chars": -1}, {"heading": ""}):
        with pytest.raises(ValidationError):
            ChunkCoverage.model_validate({**FULL, **bad})
