import pytest
from pydantic import ValidationError

from docfactory.models.fact_meta import FactMeta
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.fact_source import FactSource

MINIMAL = {
    "generated_by": "test-producer/1",
}

FULL = {
    "generated_by": "test-producer/1",
    "title": "Test title",
    "description": "One test sentence.",
    "tags": ["test-tag"],
    "sources": [{"resource": "Test-App/test-source.pdf"}],
    "stale_after": "2026-01-01T00:00:00Z",
}


def test_minimal_payload_is_valid():
    FactMeta.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FactMeta.model_validate(FULL)
    assert FactMeta.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["generated_by"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        FactMeta.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FactMeta.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = FactMeta.model_validate(MINIMAL)
    assert obj.title is None
    assert obj.description is None
    assert obj.tags == []
    assert obj.sources == []
    assert obj.stale_after is None


@pytest.mark.parametrize("field", ["generated_by"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        FactMeta.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["stale_after"])
def test_text_not_matching_the_pattern_is_rejected(field):
    with pytest.raises(ValidationError):
        FactMeta.model_validate({**FULL, field: "not matching the pattern"})


@pytest.mark.parametrize("field", ["generated_by", "title", "description", "tags", "sources", "stale_after"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FactMeta.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
