"""The generator agent loop with a scripted model (Phase 4b), and the manual entry point."""
import json
from pathlib import Path

import pytest

from docfactory import db
from docfactory.agents import run_generation
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.agents.generator_agent import GeneratorAgent, PROMPT_FILE, start_message
from docfactory.agents.prompt_file import load_prompt
from docfactory.build import build_document
from docfactory.documentmodels.documents.overview_document import OverviewDocument
from docfactory.documentsaver.shared.document_control_saver import DocumentControlSaver
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.kpis_saver import KpisSaver
from docfactory.models.fact_meta import FactMeta
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall
from docfactory.retrieval.fake_embedder import FakeEmbedder
from docfactory.retrieval.sqlite_vector_index import SqliteVectorIndex

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "json"


def _sample(folder, name):
    return json.loads((SAMPLES / folder / name).read_text(encoding="utf-8"))


def call(id, name, **arguments):
    return ModelResponse(tool_calls=[ToolCall(id=id, name=name, arguments_json=json.dumps(arguments))])


@pytest.fixture
def index(tmp_db):
    meta = FactMeta(generated_by="t/1", title="ReadmeForge overview", description="purpose of the readme generator")
    assert ApplicationOverviewSaver().save("ReadmeForge.ApplicationOverview", _sample("application_overview", "readmeforge_full.json"), meta=meta).ok
    assert KpisSaver().save("Shared.Kpis", _sample("kpis", "shared_devex_kpis_full.json"), meta=FactMeta(generated_by="t/1")).ok
    idx = SqliteVectorIndex(FakeEmbedder())
    idx.rebuild()
    return idx


def test_the_prompt_loads_without_frontmatter_and_names_the_tools_it_may_use():
    prompt = load_prompt(PROMPT_FILE)
    assert prompt.startswith("You are the **docfactory-document-generator-agent**") and "name: docfactory" not in prompt
    for tool in ("search_knowledge", "get_fact", "list_facts", "get_document", "get_document_schema", "save_document"):
        assert tool in prompt
    assert "read_okf_file" not in prompt


def test_generates_a_document_end_to_end_and_hands_the_model_only_its_own_tools(index):
    body, _ = build_document(OverviewDocument, "ReadmeForge")
    client = FakeModelClient([
        call("1", "get_document_schema", doc_type="Overview"),
        call("2", "search_knowledge", query="readme generator", app_id="ReadmeForge"),
        call("3", "get_fact", key="ReadmeForge.ApplicationOverview"),
        call("4", "save_overview_document", key="ReadmeForge.Outputs.Overview", payload=json.loads(body.model_dump_json())),
        ModelResponse(text="saved ReadmeForge.Outputs.Overview CREATED v1"),
    ])
    agent = GeneratorAgent(client, index, system="SYS")
    assert agent.run("ReadmeForge", "Overview").startswith("saved")
    system, messages, tools = client.requests[0]
    assert system == "SYS" and [t.name for t in tools] == agent.package.tool_names()
    assert messages[0].text == start_message("ReadmeForge", "Overview")
    assert db.get_row("DocumentOutputs", "ReadmeForge.Outputs.Overview")["Version"] == 1


def test_a_rejected_save_comes_back_as_feedback_the_model_can_fix(index):
    body, _ = build_document(OverviewDocument, "ReadmeForge")
    client = FakeModelClient([
        call("1", "save_overview_document", key="ReadmeForge.Outputs.Overview", payload={"bogus": 1}),
        call("2", "save_overview_document", key="ReadmeForge.Outputs.Overview", payload=json.loads(body.model_dump_json())),
        ModelResponse(text="done"),
    ])
    GeneratorAgent(client, index, system="SYS").run("ReadmeForge", "Overview")
    first_result = json.loads(client.requests[1][1][-1].text)
    assert first_result["action"] == "REJECTED" and first_result["errors"]
    assert db.get_row("DocumentOutputs", "ReadmeForge.Outputs.Overview") is not None


def test_the_agent_cannot_call_a_tool_outside_its_package(index):
    client = FakeModelClient([call("1", "save_application_overview", key="X.ApplicationOverview", payload={}), ModelResponse(text="ok")])
    GeneratorAgent(client, index, system="SYS").run("ReadmeForge", "Overview")
    assert json.loads(client.requests[1][1][-1].text)["ok"] is False


def test_the_entry_point_rejects_bad_arguments_and_missing_facts(tmp_db, capsys):
    assert run_generation.main(["ReadmeForge"]) == 2
    assert run_generation.main(["ReadmeForge", "BRD"]) == 2
    assert run_generation.main(["ReadmeForge", "Overview"]) == 1
    assert "no facts stored" in capsys.readouterr().out


def test_the_entry_point_saves_and_skips_rendering_without_control_rows(index, monkeypatch, capsys, tmp_path):
    body, _ = build_document(OverviewDocument, "ReadmeForge")
    client = FakeModelClient([call("1", "save_overview_document", key="ReadmeForge.Outputs.Overview", payload=json.loads(body.model_dump_json())),
                              ModelResponse(text="summary")])
    monkeypatch.setattr(run_generation, "default_client", lambda: client)
    monkeypatch.setattr(run_generation, "default_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr(run_generation, "load_env_file", lambda: None)
    monkeypatch.setattr(run_generation, "PROJECT_ROOT", tmp_path)
    assert run_generation.main(["ReadmeForge", "Overview"]) == 0
    out = capsys.readouterr().out
    assert "saved ReadmeForge.Outputs.Overview: version 1" in out and "not rendered" in out
    assert not (tmp_path / "output").exists()
