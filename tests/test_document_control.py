import pytest
from pydantic import ValidationError

from docfactory.documentmodels.document_control import DocumentControl
from docfactory.models.not_applicable import NotApplicable

MINIMAL = {
    "document_id": "KitchenHQ-SMTD-001",
    "title": "KitchenHQ SMTD",
}

FULL = {
    "document_id": "KitchenHQ-SMTD-001",
    "title": "KitchenHQ SMTD",
    "document_version": "1.0",
    "status": "Draft",
    "owner": "QA Lead",
    "approvers": ["Engineering Manager", "QA Lead"],
    "created_date": "2024-01-15",
    "last_updated_date": "2024-02-01",
}


def test_minimal_payload_is_valid():
    DocumentControl.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = DocumentControl.model_validate(FULL)
    assert DocumentControl.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["document_id", "title"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        DocumentControl.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        DocumentControl.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = DocumentControl.model_validate(MINIMAL)
    assert obj.document_version == ''
    assert obj.status == ''
    assert obj.owner == ''
    assert obj.approvers == []
    assert obj.created_date is None
    assert obj.last_updated_date is None


@pytest.mark.parametrize("field", ["document_id", "title"])
def test_empty_text_is_rejected_where_min_length_is_set(field):
    with pytest.raises(ValidationError):
        DocumentControl.model_validate({**FULL, field: ""})


@pytest.mark.parametrize("field", ["document_id", "title", "document_version", "status", "owner", "approvers", "created_date", "last_updated_date"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        DocumentControl.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
