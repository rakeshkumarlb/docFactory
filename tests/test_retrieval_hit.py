import pytest
from pydantic import ValidationError

from docfactory.models.retrieval_hit import RetrievalHit
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.fact_status import FactStatus

MINIMAL = {
    "key": "Test.Fact",
    "score": 0.5,
    "title": "Test title",
    "type": "Test type",
    "status": FactStatus.DRAFT,
}

FULL = {
    "key": "Test.Fact",
    "score": 0.5,
    "title": "Test title",
    "type": "Test type",
    "status": FactStatus.DRAFT,
    "stale": True,
    "description": "Test description",
}


def test_minimal_payload_is_valid():
    RetrievalHit.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = RetrievalHit.model_validate(FULL)
    assert RetrievalHit.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["key", "score", "title", "type", "status"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        RetrievalHit.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        RetrievalHit.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = RetrievalHit.model_validate(MINIMAL)
    assert obj.stale is False
    assert obj.description is None


@pytest.mark.parametrize("field", ["key"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        RetrievalHit.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["key", "score", "title", "type", "status", "stale", "description"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        RetrievalHit.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
