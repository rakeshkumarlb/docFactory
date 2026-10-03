"""The ingestion LLM fallback (Phase 2 redesign, step 5) with a scripted model: single-tool packages, validation, pipeline wiring."""
import json
import shutil
from pathlib import Path

import pytest

from docfactory import db
from docfactory.agents import run_ingestion
from docfactory.agents.agent_loop import EMPTY_REPLY_NUDGE, AgentLoop
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.agents.ingestion_fallback import SCOPE_PROMPT, TAGGER_PROMPT, IngestionFallback
from docfactory.agents.prompt_file import load_prompt
from docfactory.ingest import pipeline
from docfactory.ingest.chunking import assemble_chunks
from docfactory.ingest.paths import DOCSTORE_ENV, INCOMING_ENV, STAGING_ENV
from docfactory.models.ingest_outcome import IngestOutcome
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall
from docfactory.tools.ingestion_tools import scope_package, tagging_package

CORPUS = Path(__file__).parent / "corpus" / "incoming"
CLOCK = lambda: "2026-10-03T12:00:00+00:00"  # noqa: E731


def call(name, **arguments):
    return ModelResponse(tool_calls=[ToolCall(id=f"c_{name}", name=name, arguments_json=json.dumps(arguments))])


def fake(*responses):
    client = FakeModelClient(list(responses))
    client.model = "fake"
    return client


CHUNKS = assemble_chunks([("text", "Acme Platform", 1), ("heading", 1, "4. Interfaces", 2), ("text", "REST APIs to the HR system.", 2),
                          ("heading", 1, "6. Glossary", 3), ("text", "API: application programming interface", 3)])


# --- packages ----------------------------------------------------------------------------------------------------------------

def test_each_fallback_package_holds_exactly_one_tool():
    assert tagging_package({1}, ["Architecture"], []).tool_names() == ["submit_chunk_tags"]
    assert scope_package([]).tool_names() == ["submit_scope"]


def test_submit_chunk_tags_validates_entities_and_chunk_numbers():
    accepted = []
    package = tagging_package({2, 3}, ["Architecture", "Support"], accepted)
    bad = package.call("submit_chunk_tags", {"tags": [{"chunk_no": 2, "entities": ["Made Up"], "reason": "x"},
                                                       {"chunk_no": 9, "entities": [], "reason": "x"}]})
    assert bad["ok"] is False and "unknown entity 'Made Up'" in bad["error"] and "chunk 9 was not asked" in bad["error"]
    assert "no answer for chunks [3]" in bad["error"] and accepted == []
    good = package.call("submit_chunk_tags", {"tags": [{"chunk_no": 2, "entities": ["Architecture"], "reason": "REST APIs"},
                                                        {"chunk_no": 3, "entities": [], "reason": "glossary"}]})
    assert good == {"ok": True, "accepted": 2} and len(accepted[0]) == 2


def test_submit_scope_normalises_the_folder_and_allows_null():
    accepted = []
    package = scope_package(accepted)
    assert package.call("submit_scope", {"scope": "Acme Platform", "reason": "title"})["scope"] == "Acme-Platform"
    assert package.call("submit_scope", {"scope": "Shared", "reason": "standard"})["scope"] == "shared"
    assert package.call("submit_scope", {"scope": None, "reason": "personal notes"})["scope"] is None
    assert package.call("submit_scope", {"scope": "!!!", "reason": "x"})["ok"] is False
    assert accepted == [("Acme-Platform", "title"), ("shared", "standard"), (None, "personal notes")]


def test_the_prompts_load_and_name_their_tool():
    assert "submit_chunk_tags" in load_prompt(TAGGER_PROMPT) and "submit_scope" in load_prompt(SCOPE_PROMPT)


# --- the fallback ------------------------------------------------------------------------------------------------------------

def test_tag_chunks_sends_only_the_unmapped_chunks_and_returns_llm_tags():
    client = fake(call("submit_chunk_tags", tags=[{"chunk_no": 2, "entities": ["Architecture"], "reason": "'REST APIs to the HR system'"},
                                                  {"chunk_no": 3, "entities": [], "reason": "glossary"}]),
                  ModelResponse(text="done"))
    tags, note = IngestionFallback(client).tag_chunks(CHUNKS[1:])
    assert note == "" and [(t.chunk_no, t.entity, t.origin, t.score) for t in tags] == [(2, "Architecture", "llm/fake", 0)]
    message = client.requests[0][1][0].text
    assert "[chunk 2] 4. Interfaces" in message and "[chunk 1]" not in message and "- FunctionalRequirements:" in message
    assert [t.name for t in client.requests[0][2]] == ["submit_chunk_tags"]


def test_a_rejected_answer_is_fed_back_and_the_corrected_one_wins():
    client = fake(call("submit_chunk_tags", tags=[{"chunk_no": 2, "entities": ["Interfaces"], "reason": "x"}]),
                  call("submit_chunk_tags", tags=[{"chunk_no": 2, "entities": ["Architecture"], "reason": "APIs"}]),
                  ModelResponse(text="fixed"))
    tags, _ = IngestionFallback(client).tag_chunks(CHUNKS[1:2])
    assert [t.entity for t in tags] == ["Architecture"]
    assert "unknown entity 'Interfaces'" in client.requests[1][1][-1].text


def test_no_answer_or_a_failure_gives_nothing_never_an_exception():
    assert IngestionFallback(fake(ModelResponse(text="I cannot"))).tag_chunks(CHUNKS[1:2]) == ([], "tag fallback gave no answer")
    tags, note = IngestionFallback(fake(ModelResponse(text=""), ModelResponse(text=""))).tag_chunks(CHUNKS[1:2])
    assert tags == [] and "empty reply twice" in note


def test_decide_scope_returns_the_folder_or_none():
    client = fake(call("submit_scope", scope="Acme Platform", reason="'Acme Platform' on the cover"), ModelResponse(text="ok"))
    assert IngestionFallback(client).decide_scope(CHUNKS, [], ["ReadmeForge"], "unconfident") == ("Acme-Platform", "'Acme Platform' on the cover")
    assert "Existing scope folders: ReadmeForge" in client.requests[0][1][0].text
    unsure = fake(call("submit_scope", scope=None, reason="personal notes"), ModelResponse(text="ok"))
    assert IngestionFallback(unsure).decide_scope(CHUNKS, [], [], "x") == (None, "personal notes")


def test_an_empty_reply_is_nudged_once_then_fails():
    client = fake(ModelResponse(text=""), ModelResponse(text="answer"))
    assert AgentLoop(client, scope_package([]), "SYS", "go").run() == "answer"
    assert client.requests[1][1][-1].text == EMPTY_REPLY_NUDGE
    with pytest.raises(RuntimeError, match="empty reply twice"):
        AgentLoop(fake(ModelResponse(text=""), ModelResponse(text=" ")), scope_package([]), "SYS", "go").run()


# --- wired into the pipeline -------------------------------------------------------------------------------------------------

@pytest.fixture
def dirs(tmp_db, tmp_path, monkeypatch):
    paths = {name: tmp_path / name for name in ("incoming", "staging", "DocStore")}
    for path in paths.values():
        path.mkdir()
    monkeypatch.setenv(INCOMING_ENV, str(paths["incoming"]))
    monkeypatch.setenv(STAGING_ENV, str(paths["staging"]))
    monkeypatch.setenv(DOCSTORE_ENV, str(paths["DocStore"]))
    return paths


def test_the_fallback_tags_and_places_a_standard_the_rules_could_not(dirs):
    shutil.copyfile(CORPUS / "Platform Reliability Standards 2026.pdf", dirs["incoming"] / "standards.pdf")
    client = fake(
        call("submit_chunk_tags", tags=[{"chunk_no": 1, "entities": [], "reason": "title"},
                                        {"chunk_no": 2, "entities": [], "reason": "scope statement"},
                                        {"chunk_no": 3, "entities": ["Slo"], "reason": "'Production availability: 99.9%'"},
                                        {"chunk_no": 4, "entities": [], "reason": "review cycle"}]),
        ModelResponse(text="tagged"),
    )
    [report] = pipeline.run_ingest(CLOCK, IngestionFallback(client))
    assert (report.outcome, report.target_path) == (IngestOutcome.NEW, "shared/standards.pdf")  # shared follows from the Slo-only tags
    assert report.entity_summary == ["Slo: 1 chunks (1 by llm/fake)"] and report.unmapped_chunks == [1, 2, 4]
    tags = db.list_doc_chunk_tags("shared/standards.pdf")
    assert [(t["ChunkNo"], t["Entity"], t["Origin"]) for t in tags] == [(3, "Slo", "llm/fake")]


def test_an_unsure_llm_scope_leaves_the_file_in_staging_with_both_reasons(dirs):
    shutil.copyfile(CORPUS / "notes.txt", dirs["incoming"] / "notes.txt")
    client = fake(call("submit_chunk_tags", tags=[{"chunk_no": 1, "entities": [], "reason": "personal to-do list"}]), ModelResponse(text="ok"),
                  call("submit_scope", scope=None, reason="personal notes, no application named"), ModelResponse(text="ok"))
    [report] = pipeline.run_ingest(CLOCK, IngestionFallback(client))
    assert report.outcome == IngestOutcome.STAGED
    assert "scope unsure" in report.reason and "llm/fake: personal notes" in report.reason
    assert (dirs["staging"] / "notes.txt").is_file()


def test_an_llm_scope_reuses_an_existing_folder_spelled_differently(dirs):
    (dirs["DocStore"] / "Acme-Platform").mkdir()
    (dirs["incoming"] / "intro.md").write_text("Some notes about the platform.\n", encoding="utf-8")
    client = fake(call("submit_chunk_tags", tags=[{"chunk_no": 1, "entities": [], "reason": "x"}]), ModelResponse(text="ok"),
                  call("submit_scope", scope="ACME platform", reason="named"), ModelResponse(text="ok"))
    [report] = pipeline.run_ingest(CLOCK, IngestionFallback(client))
    assert report.target_path == "Acme-Platform/intro.md"


def test_the_entry_point_runs_rules_only_with_no_llm_and_rejects_unknown_flags(dirs, monkeypatch, capsys):
    monkeypatch.setattr(run_ingestion, "load_env_file", lambda: None)
    monkeypatch.setattr(run_ingestion, "default_client", lambda: (_ for _ in ()).throw(AssertionError("no LLM expected")))
    assert run_ingestion.main(["--no-llm"]) == 0 and "nothing to ingest" in capsys.readouterr().out
    assert run_ingestion.main(["--bogus"]) == 2
