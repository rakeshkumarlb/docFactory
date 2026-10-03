import pytest
from pydantic import ValidationError

from docfactory.models.file_info import FileInfo
from docfactory.models.not_applicable import NotApplicable
from pydantic import NonNegativeInt

MINIMAL = {
    "path": "test-file.txt",
    "size_bytes": 0,
    "hashcode": "0" * 64,
}

FULL = {
    "path": "test-file.txt",
    "size_bytes": 0,
    "hashcode": "0" * 64,
}


def test_minimal_payload_is_valid():
    FileInfo.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FileInfo.model_validate(FULL)
    assert FileInfo.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["path", "size_bytes", "hashcode"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        FileInfo.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FileInfo.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field", ["path", "hashcode"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        FileInfo.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["path", "size_bytes", "hashcode"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FileInfo.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
