"""The generator tool package (Phase 4b): exact tool list, least privilege, search, reading knowledge files, document saving."""
import json
from pathlib import Path

import pytest

from docfactory import db
from docfactory.build import build_document
from docfactory.documentmodels.documents.overview_document import OverviewDocument
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.kpis_saver import KpisSaver
from docfactory.models.fact_meta import FactMeta
from docfactory.retrieval.fake_embedder import FakeEmbedder
from docfactory.retrieval.sqlite_vector_index import SqliteVectorIndex
from docfactory.tools.generation_tools import generation_package, generation_tool_names

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "json"

EXPECTED_TOOLS = ["search_knowledge", "read_okf_file", "get_fact", "list_facts", "get_document", "get_document_schema", "save_document",
                  "save_overview_document", "save_smtd_document", "save_sop_document", "save_srs_document"]


def _sample(folder, name):
    return json.loads((SAMPLES / folder / name).read_text(encoding="utf-8"))


@pytest.fixture
def package(tmp_db):
    meta = FactMeta(generated_by="t/1", title="ReadmeForge overview", description="purpose of the readme generator")
    assert ApplicationOverviewSaver().save("ReadmeForge.ApplicationOverview", _sample("application_overview", "readmeforge_full.json"), meta=meta).ok
    assert KpisSaver().save("Shared.Kpis", _sample("kpis", "shared_devex_kpis_full.json"), meta=FactMeta(generated_by="t/1", title="Shared KPIs")).ok
    index = SqliteVectorIndex(FakeEmbedder())
    index.rebuild()
    return generation_package(index)


def test_the_package_holds_exactly_the_agreed_tools(package):
    assert package.tool_names() == EXPECTED_TOOLS == generation_tool_names()


def test_least_privilege_no_entity_savers_no_file_tools_no_control_savers(package):
    names = set(package.tool_names())
    assert not {n for n in names if n.startswith("save_") and n not in {"save_document", *EXPECTED_TOOLS}}
    assert not names & {"save_fact", "save_application_overview", "store_file", "defer_file", "read_docstore_text", "list_docstore",
                        "save_document_control", "save_revision_history"}


def test_a_tool_outside_the_package_is_refused(package):
    with pytest.raises(PermissionError):
        package.call("save_fact", {"key": "ReadmeForge.Architecture", "payload": {}})


def test_schemas_are_derived_and_typed_savers_publish_the_document_schema(package):
    specs = {t.name: t.input_schema() for t in package.tools()}
    payload = specs["save_overview_document"]["properties"]["payload"]
    assert "application_summary" in payload["properties"] and "$ref" not in json.dumps(payload)
    assert set(specs["search_knowledge"]["properties"]) == {"query", "app_id", "limit", "include_deprecated"}


def test_search_knowledge_returns_hits_with_status(package):
    hits = package.call("search_knowledge", {"query": "readme generator purpose", "app_id": "ReadmeForge"})
    assert hits[0]["key"] == "ReadmeForge.ApplicationOverview" and hits[0]["status"] == "draft" and hits[0]["stale"] is False
    assert {h["key"] for h in hits} == {"ReadmeForge.ApplicationOverview", "Shared.Kpis"}


def test_read_okf_file_returns_the_file_and_feedback_for_unknown_keys(package):
    result = package.call("read_okf_file", {"key": "ReadmeForge.ApplicationOverview"})
    assert result["text"].startswith("---") and "ReadmeForge" in result["text"] and result["links"] == [] and result["status"] == "draft"
    assert package.call("read_okf_file", {"key": "Nope.Thing"})["ok"] is False


def test_get_document_schema_by_type_and_unknown_type(package):
    schema = package.call("get_document_schema", {"doc_type": "SRS"})
    assert "functional_requirements" in schema["properties"]
    assert package.call("get_document_schema", {"doc_type": "BRD"})["ok"] is False


def test_save_document_saves_and_get_document_reads_it_back(package):
    body, _ = build_document(OverviewDocument, "ReadmeForge")
    payload = json.loads(body.model_dump_json())
    result = package.call("save_overview_document", {"key": "ReadmeForge.Outputs.Overview", "payload": payload})
    assert result["ok"] and result["action"] == "CREATED"
    assert package.call("get_document", {"key": "ReadmeForge.Outputs.Overview"})["version"] == 1
    again = package.call("save_document", {"key": "ReadmeForge.Outputs.Overview", "payload": payload})
    assert again["action"] == "UNCHANGED"
    assert package.call("get_document", {"key": "Nope.Outputs.Overview"}) is None


def test_a_bad_document_is_rejected_with_feedback_and_nothing_is_written(package):
    result = package.call("save_overview_document", {"key": "ReadmeForge.Outputs.Overview", "payload": {"made_up": 1}})
    assert result["ok"] is False and result["action"] == "REJECTED" and result["errors"]
    assert db.get_row("DocumentOutputs", "ReadmeForge.Outputs.Overview") is None


def test_save_document_refuses_a_key_no_document_saver_owns(package):
    assert package.call("save_document", {"key": "ReadmeForge.Architecture", "payload": {}})["ok"] is False
    assert package.call("save_document", {"key": "ReadmeForge.Outputs.SMTD.DocumentControl", "payload": {}})["ok"] is False
