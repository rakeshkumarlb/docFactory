import pytest
from pydantic import ValidationError

from docfactory.models.fact_contribution import FactContribution
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "fact_key": "Test-App.TestFact",
    "resource": "Test-App/test-file.pdf",
    "value_json": "{\"test\":1}",
    "hashcode": "0" * 64,
    "generated_by": "test-agent/1",
    "timestamp": "2026-01-01T00:00:00+00:00",
}

FULL = {
    "fact_key": "Test-App.TestFact",
    "resource": "Test-App/test-file.pdf",
    "value_json": "{\"test\":1}",
    "hashcode": "0" * 64,
    "chunks_hash": "1" * 64,
    "description": "Test description.",
    "generated_by": "test-agent/1",
    "timestamp": "2026-01-01T00:00:00+00:00",
}


def test_minimal_payload_is_valid():
    FactContribution.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FactContribution.model_validate(FULL)
    assert FactContribution.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["fact_key", "resource", "value_json", "hashcode", "generated_by", "timestamp"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        FactContribution.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FactContribution.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = FactContribution.model_validate(MINIMAL)
    assert obj.chunks_hash is None
    assert obj.description is None


@pytest.mark.parametrize("field", ["fact_key", "resource", "value_json", "generated_by", "timestamp"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        FactContribution.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["hashcode"])
def test_text_not_matching_the_pattern_is_rejected(field):
    with pytest.raises(ValidationError):
        FactContribution.model_validate({**FULL, field: "not matching the pattern"})


@pytest.mark.parametrize("field", ["fact_key", "resource", "value_json", "hashcode", "chunks_hash", "description", "generated_by", "timestamp"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FactContribution.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
