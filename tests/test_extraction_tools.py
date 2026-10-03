"""The extraction tool package (Phase 3b): exact tool list, schemas from the models, actor and sources set by code."""
import json
from pathlib import Path

import pytest

from docfactory import bundle, db
from docfactory.ingest import docstore_reads as ops
from docfactory.ingest.paths import DOCSTORE_ENV
from docfactory.tools.extraction_tools import extraction_package, extraction_tool_names

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "json"
ACTOR = "okf-extraction-agent/test-model"
SRS = "ReadmeForge/srs.txt"
STAMP = "2026-10-01T09:00:00+00:00"

EXPECTED_TOOLS = [
    "list_docstore", "read_docstore_text", "get_fact", "list_facts", "save_fact",
    "save_application_overview", "save_architecture", "save_backup_recovery", "save_deployment", "save_environments",
    "save_functional_requirements", "save_known_errors", "save_kpis", "save_monitoring", "save_non_functional_requirements",
    "save_slo", "save_sop", "save_support",
]


@pytest.fixture
def package(tmp_db, tmp_path, monkeypatch):
    store = tmp_path / "DocStore"
    (store / "ReadmeForge").mkdir(parents=True)
    (store / SRS).write_text("FR-001 The system shall scan on push.", encoding="utf-8")
    monkeypatch.setenv(DOCSTORE_ENV, str(store))
    db.commit_ingested(SRS, "hash", STAMP, [(1, "Requirements", None, None, "FR-001 The system shall scan on push.", "0" * 64)], [])
    return extraction_package(ACTOR)


def _payload(name="readmeforge_minimal.json"):
    return json.loads((SAMPLES / "functional_requirements" / name).read_text(encoding="utf-8"))


def test_the_package_holds_exactly_these_tools(tmp_db):
    assert extraction_package(ACTOR).tool_names() == EXPECTED_TOOLS == extraction_tool_names()


def test_the_package_has_no_file_moving_ingestion_or_document_tools(tmp_db):
    names = set(extraction_tool_names())
    assert not names & {"list_incoming", "read_incoming_text", "search_docstore", "compare_with_docstore", "store_file", "defer_file"}
    assert not any("document" in name and name != "list_docstore" and name != "read_docstore_text" for name in names)


def test_a_tool_outside_the_package_is_refused(package):
    with pytest.raises(PermissionError, match="not in the extraction package"):
        package.call("store_file", {"incoming_path": "x", "target_path": "y"})


def test_typed_save_schemas_come_from_the_models_without_dangling_references(package):
    schema = {t.name: t.input_schema() for t in package.tools()}["save_functional_requirements"]
    assert "$ref" not in json.dumps(schema) and "$defs" not in json.dumps(schema)
    payload = schema["properties"]["payload"]
    assert payload["description"].startswith("The functional requirements")
    item = payload["properties"]["requirements"]["items"]
    assert item["properties"]["id"]["description"] and "id" in item["required"]
    assert set(schema["required"]) == {"key", "payload"}
    assert set(schema["properties"]) == {"key", "payload", "title", "description", "tags", "sources", "stale_after"}  # no generated_by: the actor is fixed by code


def test_every_tool_has_a_description_and_the_save_tools_say_which_key(package):
    for tool in package.tools():
        assert tool.description.strip()
    typed = {t.name: t for t in package.tools()}
    assert "<App>.FunctionalRequirements" in typed["save_functional_requirements"].description
    assert "'Shared.Kpis'" in typed["save_kpis"].description


def test_a_typed_save_stores_the_fact_with_the_actor_and_the_docstore_source(package):
    result = package.call("save_functional_requirements", {
        "key": "ReadmeForge.FunctionalRequirements", "payload": _payload(), "sources": [SRS], "description": "What it must do.", "tags": ["srs"],
        "generated_by": "someone-else/forged",
    })
    assert result["ok"] and result["action"] == "CREATED" and result["version"] == 1
    row = db.get_row("KnowledgeFacts", "ReadmeForge.FunctionalRequirements")
    assert row["GeneratedBy"] == ACTOR and row["Status"] == "draft"
    assert "last_modified: " + STAMP in row["YmlFrontmatter"] and f'resource: "{SRS}"' in row["YmlFrontmatter"]
    assert db.list_fact_keys_by_source(SRS) == ["ReadmeForge.FunctionalRequirements"]
    assert (bundle.bundles_root() / "ReadmeForge" / "FunctionalRequirements.md").is_file()


def test_a_second_save_with_a_changed_value_updates_and_records_history(package):
    key = "ReadmeForge.FunctionalRequirements"
    package.call("save_functional_requirements", {"key": key, "payload": _payload(), "sources": [SRS]})
    result = package.call("save_functional_requirements", {"key": key, "payload": _payload("readmeforge_full.json"), "sources": [SRS]})
    assert result["action"] == "UPDATED" and result["version"] == 2
    assert [h["Version"] for h in db.list_fact_history(key)] == [2]


def test_a_source_that_is_not_in_the_docstore_is_feedback_and_writes_nothing(package):
    result = package.call("save_functional_requirements", {"key": "ReadmeForge.FunctionalRequirements", "payload": _payload(), "sources": ["ReadmeForge/made-up.pdf"]})
    assert result["ok"] is False and "not in the DocStore" in result["error"]
    assert db.list_rows("KnowledgeFacts") == []


def test_a_bad_payload_comes_back_as_structured_feedback(package):
    result = package.call("save_functional_requirements", {"key": "ReadmeForge.FunctionalRequirements", "payload": {"requirements": [{"id": "FR-001"}]}})
    assert result["ok"] is False and result["action"] == "REJECTED"
    error = result["errors"][0]
    assert error["path"] == "requirements.0.title" and error["field_description"] and error["question"]
    assert db.list_rows("KnowledgeFacts") == []


def test_a_typed_save_under_the_wrong_entitys_key_is_rejected(package):
    result = package.call("save_functional_requirements", {"key": "ReadmeForge.Architecture", "payload": _payload()})
    assert result["action"] == "REJECTED" and result["errors"][0]["error_type"] == "key_pattern_mismatch"


def test_save_fact_dispatches_by_key_and_refuses_unknown_keys(package):
    ok = package.call("save_fact", {"key": "ReadmeForge.FunctionalRequirements", "payload": _payload(), "sources": [SRS]})
    assert ok["action"] == "CREATED"
    unknown = package.call("save_fact", {"key": "ReadmeForge.Nothing", "payload": {}})
    assert unknown["ok"] is False and "no entity saver accepts key" in unknown["error"] and "{app}.Architecture" in unknown["error"]


def test_get_fact_and_list_facts_read_back_what_was_saved(package):
    assert package.call("get_fact", {"key": "ReadmeForge.FunctionalRequirements"}) is None
    package.call("save_fact", {"key": "ReadmeForge.FunctionalRequirements", "payload": _payload()})
    fact = package.call("get_fact", {"key": "ReadmeForge.FunctionalRequirements"})
    assert fact["version"] == 1 and json.loads(fact["value"])["requirements"][0]["id"] == "FR-001"
    assert [f["key"] for f in package.call("list_facts", {})] == ["ReadmeForge.FunctionalRequirements"]
    assert package.call("list_facts", {"app_id": "Other"}) == []


def test_list_docstore_and_read_docstore_text(package):
    assert [r["FullPath"] for r in package.call("list_docstore", {})] == [SRS]
    assert package.call("list_docstore", {"folder": "shared"}) == []
    assert package.call("read_docstore_text", {"path": SRS}) == "## Requirements\nFR-001 The system shall scan on push."


def test_read_docstore_text_is_rebuilt_from_the_chunks_and_needs_them(package, tmp_path):
    store = tmp_path / "DocStore"
    (store / "ReadmeForge" / "spec.pdf").write_bytes(b"%PDF binary")
    db.commit_ingested("ReadmeForge/spec.pdf", "h2", STAMP, [(1, "1. A", 1, 1, "one", "1" * 64), (2, "1. A > 1.1. B", 2, 2, "two", "2" * 64)], [])
    assert ops.read_docstore_text("ReadmeForge/spec.pdf") == "## 1. A\none\n\n## 1. A > 1.1. B\ntwo"
    db.write_docstore_row("ReadmeForge/raw.pdf", "h3", STAMP)
    result = package.call("read_docstore_text", {"path": "ReadmeForge/raw.pdf"})
    assert result["ok"] is False and "chunk_rebuild" in result["error"]


@pytest.mark.parametrize("path", ["ReadmeForge/not-tracked.txt", "../outside.txt", "/etc/passwd", ""])
def test_read_docstore_text_refuses_untracked_and_escaping_paths(package, tmp_path, path):
    (tmp_path / "outside.txt").write_text("secret", encoding="utf-8")
    result = package.call("read_docstore_text", {"path": path})
    assert result["ok"] is False
