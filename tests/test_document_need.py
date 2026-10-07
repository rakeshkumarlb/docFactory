import pytest
from pydantic import ValidationError

from docfactory.documentmodels.shared.document_need import DocumentNeed
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "question": "Test question?",
    "gaps": [1],
}

FULL = {
    "question": "Test question?",
    "audience": "test audience",
    "gaps": [1],
}


def test_minimal_payload_is_valid():
    DocumentNeed.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = DocumentNeed.model_validate(FULL)
    assert DocumentNeed.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["question", "gaps"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        DocumentNeed.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        DocumentNeed.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = DocumentNeed.model_validate(MINIMAL)
    assert obj.audience == ''


@pytest.mark.parametrize("field", ["question"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        DocumentNeed.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["question", "audience", "gaps"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        DocumentNeed.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})


def test_a_need_must_cover_at_least_one_gap():
    with pytest.raises(ValidationError):
        DocumentNeed.model_validate({**FULL, "gaps": []})


def test_gap_numbers_must_be_integers():
    with pytest.raises(ValidationError):
        DocumentNeed.model_validate({**FULL, "gaps": ["one"]})
