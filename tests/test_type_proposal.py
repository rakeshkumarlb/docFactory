import pytest
from pydantic import ValidationError

from docfactory.models.type_proposal import TypeProposal

MINIMAL = {"entity": "Risks", "doc": "The risks of an application with their likelihood.", "fields": [{"name": "summary", "description": "What the register says, e.g. three risks.", "question": "What does it say?"}], "heading_terms": ["risk register"], "sample_chunks": [3], "rationale": "No entity covers risks."}
FULL = {"entity": "Risks", "doc": "The risks of an application with their likelihood.", "scope": "shared", "fields": [{"name": "summary", "description": "What the register says, e.g. three risks.", "question": "What does it say?"}], "list_name": "risks", "item_entity": "Risk", "item_doc": "One risk.", "item_fields": [{"name": "name", "description": "Short name of the risk, e.g. delay.", "question": "What is it called?"}], "heading_terms": ["risk register"], "id_patterns": ["RISK-1"], "keywords": ["likelihood"], "sample_chunks": [3], "rationale": "No entity covers risks.", "source_path": "A/references/a.pdf", "proposed_by": "okf/x"}


def test_minimal_payload_is_valid():
    TypeProposal.model_validate(MINIMAL)


def test_full_payload_round_trips():
    obj = TypeProposal.model_validate(FULL)
    assert TypeProposal.model_validate(obj.model_dump()) == obj


@pytest.mark.parametrize("field", ["entity", "doc", "fields", "heading_terms", "sample_chunks", "rationale"])
def test_missing_mandatory_field_is_rejected(field):
    payload = {k: v for k, v in FULL.items() if k != field}
    with pytest.raises(ValidationError) as caught:
        TypeProposal.model_validate(payload)
    assert field in {error["loc"][0] for error in caught.value.errors()}


def test_extra_field_is_rejected():
    with pytest.raises(ValidationError):
        TypeProposal.model_validate({**FULL, "not_a_field": "x"})


def test_defaults():
    obj = TypeProposal.model_validate(MINIMAL)
    assert (obj.scope, obj.list_name, obj.item_entity, obj.item_doc, obj.item_fields, obj.id_patterns, obj.keywords, obj.source_path, obj.proposed_by) == ("app", "", "", "", [], [], [], "", "")


def test_entity_scope_and_lists_are_checked():
    for bad in ({"entity": "risks"}, {"scope": "global"}, {"fields": []}, {"heading_terms": []}, {"sample_chunks": []}, {"doc": "short"}):
        with pytest.raises(ValidationError):
            TypeProposal.model_validate({**FULL, **bad})
