"""Entity resolution: the submit_merges tool, the resolution store, folding duplicates in the merge, skipping unchanged types."""
import json

import pytest

from docfactory.agents.duplicate_resolver import DuplicateResolver
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.paths import bundle_root, resolution_relpath
from docfactory.bundle.resolution_store import ResolutionStore
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.entity_record import EntityRecord
from docfactory.models.file_recognition import FileRecognition
from docfactory.models.model_response import ModelResponse
from docfactory.models.recognized_entity import RecognizedEntity
from docfactory.models.recognized_relation import RecognizedRelation
from docfactory.models.resolution_group import ResolutionGroup
from docfactory.models.tool_call import ToolCall
from docfactory.models.window_recognition import WindowRecognition
from docfactory.recognize.duplicate_resolution import resolve_scope, type_hashes
from docfactory.recognize.entity_merge import merge_entities
from docfactory.tools.resolution_tools import RESOLUTION_TOOL_NAMES, resolution_package

IDS = {"Component/matching-engine", "Component/ai-engine", "Component/web-frontend"}


def entity(entity_id, name, type_="Component"):
    return EntityRecord(entity_id=entity_id, scope="App", type=type_, name=name)


def test_the_tool_accepts_groups_and_refuses_bad_ones():
    assert RESOLUTION_TOOL_NAMES == ["submit_merges"]
    accepted = []
    package = resolution_package(IDS, accepted)
    ok = package.call("submit_merges", {"groups": [{"keep": "Component/matching-engine", "same": ["Component/ai-engine"], "reason": "Same."}]})
    assert ok == {"ok": True, "groups": 1} and accepted[0][0].same == ["Component/ai-engine"]
    for groups, expected in [
        ([{"keep": "Component/matching-engine", "same": ["Component/billing"]}], "not ids of the listed entities"),
        ([{"keep": "Component/matching-engine", "same": []}], "no 'same' ids"),
        ([{"keep": "Component/ai-engine", "same": ["Component/ai-engine"]}], "also in 'same'"),
        ([{"keep": "Component/matching-engine", "same": ["Component/ai-engine"]}, {"keep": "Component/web-frontend", "same": ["Component/ai-engine"]}], "already in another group"),
    ]:
        result = resolution_package(IDS, []).call("submit_merges", {"groups": groups})
        assert result["ok"] is False and any(expected in e for e in result["errors"]), expected


def test_store_round_trip_and_tamper_check(tmp_bundle):
    store = ResolutionStore()
    group = ResolutionGroup(keep="Component/matching-engine", same=["Component/ai-engine"], reason="Same.")
    saved = store.save("App", [group], ["Component=abc"], "t/1", "2026-10-12T10:00:00Z")
    assert store.get("App") == saved and store.get("Other") is None
    path = bundle_root() / resolution_relpath("App")
    path.write_text(path.read_text(encoding="utf-8").replace("ai-engine", "web-frontend"), encoding="utf-8")
    with pytest.raises(BundleError, match="edited outside the system"):
        store.get("App")


def recognition(resource, entities, relations=()):
    window = WindowRecognition(window_hash="0" * 64, chunk_nos=[1], entities=entities, relations=list(relations))
    data = [window.model_dump(mode="json")]
    return FileRecognition(resource=resource, windows=[window], hashcode=sha256_hex(canonical_json(data)), generated_by="t/1", timestamp="2026-01-01T00:00:00Z")


def test_the_merge_folds_duplicates_and_redirects_links():
    recs = [recognition("App/references/a.md", [RecognizedEntity(name="AI-Driven Matching Engine", type="Component", chunks=[1]),
                                                RecognizedEntity(name="AI Engine", type="Component", summary="Ranks.", chunks=[1]),
                                                RecognizedEntity(name="Search Index", type="DataStore", chunks=[1])],
                        [RecognizedRelation(source="AI Engine", target="Search Index", relation="depends on")])]
    group = ResolutionGroup(keep="Component/ai-driven-matching-engine", same=["Component/ai-engine"])
    graph, notes = merge_entities("App", recs, {}, [group])
    engine = next(e for e in graph if e.type == "Component")
    assert [e.entity_id for e in graph] == ["Component/ai-driven-matching-engine", "DataStore/search-index"] and notes == []
    assert engine.aliases == ["AI Engine"] and engine.summary == "Ranks." and engine.links[0].target == "DataStore/search-index"


def test_a_decision_across_types_or_about_gone_entities_is_skipped():
    recs = [recognition("App/references/a.md", [RecognizedEntity(name="Platform Team", type="Team", chunks=[1]),
                                                RecognizedEntity(name="Platform Team Lead", type="SupportContact", chunks=[1])])]
    groups = [ResolutionGroup(keep="Team/platform-team", same=["SupportContact/platform-team-lead"]),
              ResolutionGroup(keep="Team/gone", same=["Team/platform-team"])]
    graph, notes = merge_entities("App", recs, {}, groups)
    assert len(graph) == 2 and any("different types" in n for n in notes) and any("no longer in the graph" in n for n in notes)


def resolver(*groups_per_call):
    responses = []
    for groups in groups_per_call:
        responses += [ModelResponse(tool_calls=[ToolCall(id="c", name="submit_merges", arguments_json=json.dumps({"groups": groups}))]), ModelResponse(text="done")]
    client = FakeModelClient(responses)
    client.model = "fake"
    return DuplicateResolver(client, system="S"), client


def test_resolve_scope_asks_each_changed_type_once(tmp_bundle):
    graph = [entity("Component/matching-engine", "Matching Engine"), entity("Component/ai-engine", "AI Engine"),
             entity("Team/data-team", "Data Team", "Team")]  # one Team: nothing to resolve
    assert list(type_hashes(graph)) == ["Component"]
    agent, client = resolver([{"keep": "Component/matching-engine", "same": ["Component/ai-engine"], "reason": "Same."}])
    lines = resolve_scope("App", graph, agent)
    assert len(client.requests) == 2 and "Component/matching-engine = Component/ai-engine" in "\n".join(lines)
    assert ResolutionStore().get("App").groups[0].keep == "Component/matching-engine"
    agent, client = resolver()
    resolve_scope("App", graph, agent)
    assert client.requests == []  # unchanged: not asked again
    agent, client = resolver([])
    resolve_scope("App", graph + [entity("Component/web-frontend", "Web Frontend")], agent)
    assert len(client.requests) == 2 and ResolutionStore().get("App").groups == []  # the type's decisions are replaced
