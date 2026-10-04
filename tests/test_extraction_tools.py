"""The single-tool extraction package (Phase 3 redesign, step 2)."""
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.tools.extraction_tools import EXTRACTION_TOOL_NAMES, extraction_package, partial_json_schema

TEXT = "[chunk 3] 3.1. Login\nFR-01. | The system SHALL let users register."
REQ = {"id": "FR-01", "title": "Register", "description": "The system SHALL let users register."}


def package(accepted):
    return extraction_package(FunctionalRequirements, TEXT, accepted)


def test_the_package_holds_exactly_one_tool():
    assert EXTRACTION_TOOL_NAMES == ["submit_extraction"]
    assert [t.name for t in package([]).tools()] == ["submit_extraction"]


def test_the_published_schema_is_the_partial_entity_with_inlined_items():
    schema = partial_json_schema(FunctionalRequirements)
    assert set(schema["properties"]) == {"summary", "requirements", "out_of_scope"}
    assert "required" not in schema and "$defs" not in schema
    tool_schema = package([]).tools()[0].input_schema()
    assert tool_schema["required"] == ["values"]
    assert "requirements" in tool_schema["properties"]["values"]["properties"]


def test_an_accepted_answer_is_appended_and_nothing_is_written(tmp_db):
    accepted = []
    result = package(accepted).call("submit_extraction", {"values": {"requirements": [REQ]}, "summary": " Registration. "})
    assert result == {"ok": True, "fields": ["requirements"]}
    assert accepted == [({"requirements": [REQ]}, "Registration.")]


def test_an_empty_answer_is_legal():
    accepted = []
    assert package(accepted).call("submit_extraction", {"values": {}})["ok"] is True
    assert accepted == [({}, None)]


def test_an_invalid_item_returns_errors_with_the_question():
    accepted = []
    result = package(accepted).call("submit_extraction", {"values": {"requirements": [{"id": "FR-01"}]}})
    assert result["ok"] is False and accepted == []
    assert {e["path"] for e in result["errors"]} == {"requirements.0.title", "requirements.0.description"}
    assert all(e["question"] for e in result["errors"])


def test_an_identifier_not_in_the_text_is_refused():
    accepted = []
    result = package(accepted).call("submit_extraction", {"values": {"requirements": [{**REQ, "id": "FR-001"}]}})
    assert result["ok"] is False and "FR-001" in result["error"] and accepted == []


def test_items_sharing_an_identifier_are_refused():
    accepted = []
    text = TEXT + " 5) Guest User - browse listings - register prompt"
    result = extraction_package(FunctionalRequirements, text, accepted).call(
        "submit_extraction", {"values": {"requirements": [{**REQ, "id": "Guest User"}, {**REQ, "id": "guest user", "title": "Other"}]}})
    assert result["ok"] is False and "share an identifier" in result["error"] and accepted == []
