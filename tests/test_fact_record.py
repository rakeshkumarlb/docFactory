import pytest
from pydantic import ValidationError

from docfactory.models.fact_record import FactRecord
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.fact_status import FactStatus
from docfactory.models.fact_verification import FactVerification

MINIMAL = {
    "key": "TestApp.Thing",
    "value": "{}",
    "hashcode": "0" * 64,
    "completeness": 50.0,
    "version": 1,
}

FULL = {
    "key": "TestApp.Thing",
    "value": "{}",
    "hashcode": "0" * 64,
    "completeness": 50.0,
    "version": 1,
    "app_id": "TestApp",
    "frontmatter": "type: Test",
    "generated_by": "test-producer/1",
    "generated_at": "2026-01-01T00:00:00Z",
    "verified": [{"by": "human:test-user", "at": "2026-01-01T00:00:00Z"}],
    "status": FactStatus.STABLE,
    "stale_after": "2026-01-01T00:00:00Z",
    "type": "Test Type",
    "title": "Test title",
    "description": "A test description.",
    "tags": ["test-tag"],
    "sources": [{"resource": "Test/test.pdf"}],
}


def test_minimal_payload_is_valid():
    FactRecord.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = FactRecord.model_validate(FULL)
    assert FactRecord.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["key", "value", "hashcode", "completeness", "version"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        FactRecord.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        FactRecord.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = FactRecord.model_validate(MINIMAL)
    assert obj.app_id is None
    assert obj.frontmatter is None
    assert obj.generated_by is None
    assert obj.generated_at is None
    assert obj.verified == []
    assert obj.status == FactStatus.DRAFT
    assert obj.stale_after is None
    assert obj.type is None
    assert obj.title is None
    assert obj.description is None
    assert obj.tags == []
    assert obj.sources == []


@pytest.mark.parametrize("field", ["generated_at", "stale_after"])
def test_text_not_matching_the_pattern_is_rejected(field):
    with pytest.raises(ValidationError):
        FactRecord.model_validate({**FULL, field: "not matching the pattern"})


@pytest.mark.parametrize("field", ["key", "value", "hashcode", "completeness", "version", "app_id", "frontmatter", "generated_by", "generated_at", "verified", "status", "stale_after", "type", "title", "description", "tags", "sources"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        FactRecord.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
