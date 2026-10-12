import pytest
from pydantic import ValidationError

from docfactory.models.proposal_field import ProposalField
from docfactory.models.proposal_field_type import ProposalFieldType

MINIMAL = {"name": "risk_owner", "description": "Who owns the risk, e.g. the product owner.", "question": "Who owns the risk?"}
FULL = {"name": "risk_owner", "type": ProposalFieldType.TEXT_LIST, "description": "Who owns the risk, e.g. the product owner.", "question": "Who owns the risk?"}


def test_minimal_payload_is_valid():
    ProposalField.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ProposalField.model_validate(FULL)
    assert ProposalField.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["name", "description", "question"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ProposalField.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ProposalField.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = ProposalField.model_validate(MINIMAL)
    assert obj.type == ProposalFieldType.TEXT


def test_name_description_and_question_are_checked():
    for bad in ({"name": "Risk"}, {"name": "1x"}, {"description": "short"}, {"question": "No question mark"}, {"type": "dict"}):
        with pytest.raises(ValidationError):
            ProposalField.model_validate({**FULL, **bad})
