import pytest
from pydantic import ValidationError

from docfactory.models.fact_source import FactSource
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "resource": "Test-App/test-source.pdf",
}

FULL = {
    "resource": "Test-App/test-source.pdf",
    "id": "test-source",
    "title": "Test source title",
    "last_modified": "2026-01-01T00:00:00Z",
}


def test_minimal_payload_is_valid():
    FactSource.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FactSource.model_validate(FULL)
    assert FactSource.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["resource"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        FactSource.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FactSource.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = FactSource.model_validate(MINIMAL)
    assert obj.id is None
    assert obj.title is None
    assert obj.last_modified is None


@pytest.mark.parametrize("field", ["resource"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        FactSource.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["last_modified"])
def test_text_not_matching_the_pattern_is_rejected(field):
    with pytest.raises(ValidationError):
        FactSource.model_validate({**FULL, field: "not matching the pattern"})


@pytest.mark.parametrize("field", ["resource", "id", "title", "last_modified"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FactSource.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
