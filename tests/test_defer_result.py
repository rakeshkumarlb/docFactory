import pytest
from pydantic import ValidationError

from docfactory.models.defer_result import DeferResult
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "ok": True,
    "path": "test-file.txt",
    "reason": "test reason",
}

FULL = {
    "ok": True,
    "path": "test-file.txt",
    "reason": "test reason",
}


def test_minimal_payload_is_valid():
    DeferResult.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = DeferResult.model_validate(FULL)
    assert DeferResult.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["ok", "path", "reason"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        DeferResult.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        DeferResult.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field", ["path", "reason"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        DeferResult.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["ok", "path", "reason"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        DeferResult.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
