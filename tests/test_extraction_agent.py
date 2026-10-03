"""The extraction agent loop with a scripted model (Phase 3b), and the manual entry point."""
import json
from pathlib import Path

import pytest

from docfactory import bundle, db, okf_check
from docfactory.agents import run_extraction
from docfactory.agents.extraction_agent import ExtractionAgent, actor_of, load_prompt, PROMPT_FILE
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.ingest.paths import DOCSTORE_ENV
from docfactory.models.message_role import MessageRole
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "functional_requirements"
SRS = "ReadmeForge/srs.txt"
KEY = "ReadmeForge.FunctionalRequirements"


@pytest.fixture
def store(tmp_db, tmp_path, monkeypatch):
    root = tmp_path / "DocStore"
    (root / "ReadmeForge").mkdir(parents=True)
    (root / SRS).write_text("FR-001 Scan a repository on push.", encoding="utf-8")
    monkeypatch.setenv(DOCSTORE_ENV, str(root))
    db.write_docstore_row(SRS, "hash", "2026-10-01T09:00:00+00:00")
    return root


def call(id, name, **arguments):
    return ModelResponse(tool_calls=[ToolCall(id=id, name=name, arguments_json=json.dumps(arguments))])


def fake(*responses, model="fake-model"):
    client = FakeModelClient(list(responses))
    client.model = model
    return client


def sample(name):
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def test_the_prompt_loads_without_frontmatter_and_names_the_tools_it_may_use():
    prompt = load_prompt(PROMPT_FILE)
    assert prompt.startswith("You are the **docfactory-okf-extraction-agent**") and "name: docfactory" not in prompt
    for tool in ("read_docstore_text", "get_fact", "save_fact", "list_docstore", "list_facts"):
        assert tool in prompt


def test_the_actor_is_the_agent_and_the_model_and_falls_back_when_the_client_has_no_model():
    assert actor_of(fake(model="gemma4:31b")) == "okf-extraction-agent/gemma4:31b"
    assert actor_of(FakeModelClient([])) == "okf-extraction-agent/unknown"


def test_extracts_a_fact_end_to_end_and_hands_the_model_only_its_own_tools(store):
    client = fake(
        call("1", "read_docstore_text", path=SRS),
        call("2", "get_fact", key=KEY),
        call("3", "save_functional_requirements", key=KEY, payload=sample("readmeforge_minimal.json"), sources=[SRS], description="Scan on push."),
        ModelResponse(text="saved ReadmeForge.FunctionalRequirements CREATED v1"),
    )
    agent = ExtractionAgent(client, system="SYS")
    assert agent.run(SRS).startswith("saved")
    system, messages, tools = client.requests[0]
    assert system == "SYS" and [t.name for t in tools] == agent.package.tool_names()
    assert messages[0].role == MessageRole.USER and SRS in messages[0].text
    row = db.get_row("KnowledgeFacts", KEY)
    assert (row["GeneratedBy"], row["Status"], row["Version"]) == ("okf-extraction-agent/fake-model", "draft", 1)
    assert okf_check.check_bundle(bundle.bundles_root()) == []
    # the tool result of get_fact (null: no such fact yet) went back to the model
    assert json.loads(client.requests[2][1][-1].text) is None


def test_a_rejection_is_fed_back_and_the_model_can_fix_the_payload(store):
    client = fake(
        call("1", "save_functional_requirements", key=KEY, payload={"requirements": [{"id": "FR-001"}]}),
        call("2", "save_functional_requirements", key=KEY, payload=sample("readmeforge_minimal.json"), sources=[SRS]),
        ModelResponse(text="done"),
    )
    ExtractionAgent(client, system="SYS").run(SRS)
    feedback = json.loads(client.requests[1][1][-1].text)
    assert feedback["action"] == "REJECTED" and feedback["errors"][0]["path"] == "requirements.0.title"
    assert db.get_row("KnowledgeFacts", KEY)["Version"] == 1


def test_a_new_revision_updates_the_fact_and_keeps_the_history(store):
    first = fake(call("1", "save_functional_requirements", key=KEY, payload=sample("readmeforge_minimal.json"), sources=[SRS]), ModelResponse(text="ok"))
    ExtractionAgent(first, system="SYS").run(SRS)
    second = fake(call("1", "save_functional_requirements", key=KEY, payload=sample("readmeforge_full.json"), sources=[SRS]), ModelResponse(text="ok"), model="other-model")
    ExtractionAgent(second, system="SYS").run(SRS)
    row = db.get_row("KnowledgeFacts", KEY)
    assert (row["Version"], row["GeneratedBy"]) == (2, "okf-extraction-agent/other-model")
    assert [(h["Version"], h["GeneratedBy"]) for h in db.list_fact_history(KEY)] == [(2, "okf-extraction-agent/other-model")]


def test_a_tool_the_agent_does_not_have_is_refused_and_nothing_runs(store):
    client = fake(call("1", "store_file", incoming_path="a", target_path="b"), ModelResponse(text="ok"))
    ExtractionAgent(client, system="SYS").run(SRS)
    refusal = json.loads(client.requests[1][1][-1].text)
    assert refusal["ok"] is False and "not in the extraction package" in refusal["error"]


def test_the_turn_cap_stops_a_looping_model(store):
    client = fake(*[call(str(i), "list_docstore") for i in range(5)])
    with pytest.raises(RuntimeError, match="extraction agent stopped"):
        ExtractionAgent(client, system="SYS", max_turns=3).run(SRS)


def test_run_extraction_checks_its_arguments_and_the_path(store, capsys):
    assert run_extraction.main([]) == 2
    assert run_extraction.main(["ReadmeForge/missing.pdf"]) == 1
    out = capsys.readouterr().out
    assert "usage:" in out and "is not in the DocStore" in out and SRS in out
