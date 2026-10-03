import pytest
from pydantic import ValidationError

from docfactory.models.fact_verification import FactVerification
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "by": "human:test-user",
    "at": "2026-01-01T00:00:00Z",
}

FULL = {
    "by": "human:test-user",
    "at": "2026-01-01T00:00:00Z",
}


def test_minimal_payload_is_valid():
    FactVerification.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FactVerification.model_validate(FULL)
    assert FactVerification.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["by", "at"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        FactVerification.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FactVerification.model_validate({**FULL, "not_a_field": "x"})


@pytest.mark.parametrize("field", ["by"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        FactVerification.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["at"])
def test_text_not_matching_the_pattern_is_rejected(field):
    with pytest.raises(ValidationError):
        FactVerification.model_validate({**FULL, field: "not matching the pattern"})


@pytest.mark.parametrize("field", ["by", "at"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FactVerification.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
