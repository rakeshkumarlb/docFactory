"""Recognition of ingested files with a scripted model: windows, reuse of unchanged windows, split and retry, the entity graph."""
import json

import pytest

from docfactory import clock
from docfactory.agents.entity_recognizer import EntityRecognizer
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.bundle.entity_store import EntityStore
from docfactory.bundle.paths import bundle_root
from docfactory.bundle.recognition_store import RecognitionStore
from docfactory.bundle.source_store import SourceStore
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.model_response import ModelResponse
from docfactory.models.recognition_outcome import RecognitionOutcome
from docfactory.models.tool_call import ToolCall
from docfactory.recognize.recognition_pipeline import format_report, recognize_file
from docfactory.recognize.windows import WORD_CAP_ENV

A, B = "App/references/arch.md", "App/references/ops.md"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-12T10:00:00Z")


def store(path, sections, timestamp, tags=()):
    original = bundle_root() / path
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("".join(f"## {heading}\n{text}\n\n" for heading, text in sections), encoding="utf-8")
    chunks = chunk_file(original)
    SourceStore().write(path, file_sha256(original), timestamp, chunks,
                        [ChunkTag(chunk_no=no, entity=entity, origin="rule", score=4, evidence="t") for no, entity in tags])
    return chunks


def submit(entities, relations=(), topics=()):
    arguments = {"entities": entities, "relations": list(relations), "topics": list(topics)}
    return [ModelResponse(tool_calls=[ToolCall(id="c", name="submit_recognition", arguments_json=json.dumps(arguments))]), ModelResponse(text="done")]


def recognizer(*answers):
    client = FakeModelClient([response for answer in answers for response in answer])
    client.model = "fake"
    return EntityRecognizer(client, system="S"), client


ENGINE = {"name": "Matching Engine", "type": "Component", "summary": "Ranks candidates.", "chunks": [1]}
INDEX = {"name": "Search Index", "type": "DataStore", "aliases": ["OpenSearch"], "chunks": [1]}
DEPENDS = {"source": "Matching Engine", "target": "Search Index", "relation": "depends on", "kind": "depends_on", "chunks": [1]}


def test_recognize_store_and_build_the_graph(tmp_bundle):
    store(A, [("Components", "The Matching Engine depends on the Search Index (OpenSearch).")], "2026-10-01T00:00:00Z", [(1, "Architecture")])
    agent, client = recognizer(submit([ENGINE, INDEX], [DEPENDS], [{"chunk_no": 1, "facts": ["Architecture"]}]))
    report = recognize_file(A, agent)
    assert report.outcome == RecognitionOutcome.RECOGNIZED and (report.windows, report.calls, report.entities, report.relations) == (1, 1, 2, 1)
    message = client.requests[0][1][0].text
    assert "Outline:\n- Components" in message and "Catalog (entities already known" in message and "chunk 1: Architecture" in message
    assert [e.entity_id for e in EntityStore().list("App")] == ["Component/matching-engine", "DataStore/search-index"]
    assert EntityStore().get("App", "Component/matching-engine").links[0].target == "DataStore/search-index"
    assert RecognitionStore().get(A).windows[0].topics[0].facts == ["Architecture"]
    assert "entities created: 2" in format_report(report)


def test_an_unchanged_file_makes_no_call(tmp_bundle):
    store(A, [("Components", "The Matching Engine depends on the Search Index (OpenSearch).")], "2026-10-01T00:00:00Z")
    recognize_file(A, recognizer(submit([ENGINE, INDEX], [DEPENDS]))[0])
    agent, client = recognizer()
    report = recognize_file(A, agent)
    assert report.outcome == RecognitionOutcome.UNCHANGED and report.calls == 0 and report.skipped_windows == 1 and client.requests == []


def test_a_later_file_sees_the_graph_and_merges_into_it(tmp_bundle):
    store(A, [("Components", "The Matching Engine depends on the Search Index (OpenSearch).")], "2026-10-01T00:00:00Z")
    recognize_file(A, recognizer(submit([ENGINE, INDEX], [DEPENDS]))[0])
    store(B, [("Runbook", "If OpenSearch is slow, restart the AI Engine (the Matching Engine).")], "2026-10-02T00:00:00Z")
    engine_alias = {"name": "AI Engine", "type": "Component", "same_as": "Component/matching-engine", "chunks": [1]}
    agent, client = recognizer(submit([engine_alias], [{"source": "AI Engine", "target": "OpenSearch", "relation": "reads from"}]))
    recognize_file(B, agent)
    assert "DataStore/search-index | DataStore | Search Index | aka OpenSearch" in client.requests[0][1][0].text  # named in the window
    graph = {e.entity_id: e for e in EntityStore().list("App")}
    assert set(graph) == {"Component/matching-engine", "DataStore/search-index"}
    engine = graph["Component/matching-engine"]
    assert engine.aliases == ["AI Engine"] and {e.resource for e in engine.evidence} == {A, B}
    assert [(l.relation, l.resources) for l in engine.links] == [("depends on", [A]), ("reads from", [B])]


def test_a_failed_window_is_split_and_retried(tmp_bundle, monkeypatch):
    monkeypatch.setenv(WORD_CAP_ENV, "1000")
    store(A, [("One", "The Matching Engine ranks."), ("Two", "The Search Index stores.")], "2026-10-01T00:00:00Z")
    fail = [ModelResponse(text=""), ModelResponse(text="")]  # two empty replies: the loop gives up
    engine = {**ENGINE, "chunks": [1]}
    index = {"name": "Search Index", "type": "DataStore", "chunks": [2]}
    agent, _ = recognizer(fail, submit([engine]), submit([index]))
    report = recognize_file(A, agent)
    assert report.outcome == RecognitionOutcome.RECOGNIZED and report.calls == 3 and report.windows == 1
    assert any("split and retried" in note for note in report.notes)
    assert [w.chunk_nos for w in RecognitionStore().get(A).windows] == [[1], [2]]
    agent, client = recognizer()
    assert recognize_file(A, agent).calls == 0  # the halves cover the window: reused next time


def test_nothing_accepted_stores_nothing(tmp_bundle):
    store(A, [("One", "The Matching Engine ranks.")], "2026-10-01T00:00:00Z")
    agent, _ = recognizer([ModelResponse(text=""), ModelResponse(text="")])
    report = recognize_file(A, agent)
    assert report.outcome == RecognitionOutcome.FAILED and report.failed_windows == 1
    assert RecognitionStore().get(A) is None and EntityStore().list("App") == []
