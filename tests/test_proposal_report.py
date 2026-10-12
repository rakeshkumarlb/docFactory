import pytest
from pydantic import ValidationError

from docfactory.models.proposal_report import ProposalReport

MINIMAL = {"path": "Test/references/test.pdf"}
FULL = {"path": "Test/references/test.pdf", "chunks_asked": 3, "batches": 1, "failed_batches": 0, "saved": ["Risks"], "already_known": [], "reason": "r", "batch_notes": ["n"]}


def test_minimal_payload_is_valid():
    ProposalReport.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = ProposalReport.model_validate(FULL)
    assert ProposalReport.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["path"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        ProposalReport.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        ProposalReport.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = ProposalReport.model_validate(MINIMAL)
    assert (obj.chunks_asked, obj.batches, obj.failed_batches, obj.saved, obj.already_known, obj.reason, obj.batch_notes) == (0, 0, 0, [], [], "", [])
