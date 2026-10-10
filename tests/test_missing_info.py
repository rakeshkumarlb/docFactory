import pytest
from pydantic import ValidationError

from docfactory.documentmodels.missing_info import MissingInfo
from docfactory.models.not_applicable import NotApplicable
from docfactory.documentmodels.document_gap import DocumentGap
from docfactory.documentmodels.document_need import DocumentNeed
from docfactory.documentmodels.needs_origin import NeedsOrigin

MINIMAL = {
    "gaps_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "needs_origin": NeedsOrigin.LLM,
}

FULL = {
    "gaps": [],
    "needs": [],
    "gaps_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "needs_origin": NeedsOrigin.LLM,
}


def test_minimal_payload_is_valid():
    MissingInfo.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = MissingInfo.model_validate(FULL)
    assert MissingInfo.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["gaps_hash", "needs_origin"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        MissingInfo.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        MissingInfo.model_validate({**FULL, "not_a_field": "x"})


def test_optional_fields_default_to_their_declared_defaults():
    obj = MissingInfo.model_validate(MINIMAL)
    assert obj.gaps == []
    assert obj.needs == []


@pytest.mark.parametrize("field", ["gaps", "needs", "gaps_hash", "needs_origin"])
def test_not_applicable_is_rejected_where_not_allowed(field):
    with pytest.raises(ValidationError):
        MissingInfo.model_validate({**FULL, field: NotApplicable(reason="Not relevant for this test.")})
