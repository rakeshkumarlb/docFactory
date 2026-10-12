"""Entity-centric extraction with a scripted model: evidence gathering, one item per entity, code-set fields, skips, removal, fact merge."""
import hashlib
import json

import pytest

from docfactory import clock
from docfactory.agents.entity_item_extractor import EntityItemExtractor
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.contribution_store import ContributionStore
from docfactory.bundle.entity_store import EntityStore
from docfactory.bundle.paths import bundle_root, contribution_relpath, entity_resource
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.entity_evidence import evidence_lines, evidence_text, gather, neighbours
from docfactory.extract.entity_item_pipeline import extract_entity_items, item_json
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.entity_evidence import EntityEvidence
from docfactory.models.entity_link import EntityLink
from docfactory.models.entity_record import EntityRecord
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall

ARCH, TEAMS = "App/references/arch.md", "App/references/teams.md"
KEY = "App.Architecture"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-12T10:00:00Z")


def store(path, sections, timestamp="2026-10-01T00:00:00Z"):
    original = bundle_root() / path
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("".join(f"## {heading}\n{text}\n\n" for heading, text in sections), encoding="utf-8")
    SourceStore().write(path, file_sha256(original), timestamp, chunk_file(original), [])


def ev(resource, no):
    return EntityEvidence(resource=resource, chunk_no=no)


ENGINE = EntityRecord(entity_id="Component/matching-engine", scope="App", type="Component", name="Matching Engine", aliases=["AI Engine"],
                      evidence=[ev(ARCH, 1)], links=[EntityLink(target="DataStore/search-index", relation="depends on", kind="depends_on", resources=[ARCH]),
                                                     EntityLink(target="Team/matching-team", relation="is owned by", resources=[TEAMS])])
INDEX = EntityRecord(entity_id="DataStore/search-index", scope="App", type="DataStore", name="Search Index", evidence=[ev(ARCH, 2)])
TEAM = EntityRecord(entity_id="Team/matching-team", scope="App", type="Team", name="Matching Team", evidence=[ev(TEAMS, 1)])


def setup_graph(graph=(ENGINE, INDEX, TEAM)):
    store(ARCH, [("Matching Engine", "The Matching Engine is built with Python 3.12."), ("Search Index", "OpenSearch 2.13 holds candidate vectors.")])
    store(TEAMS, [("Matching Team", "The Matching Team owns the Matching Engine.")])
    EntityStore().write_all("App", list(graph), "2026-10-02T00:00:00Z")


def submit(values, summary=None):
    arguments = {"values": values} | ({"summary": summary} if summary else {})
    return [ModelResponse(tool_calls=[ToolCall(id="c", name="submit_extraction", arguments_json=json.dumps(arguments))]), ModelResponse(text="done")]


def extractor(*answers):
    client = FakeModelClient([r for answer in answers for r in answer])
    client.model = "fake"
    return EntityItemExtractor(client, system="S"), client


def test_neighbours_and_gather_put_own_chunks_first():
    chunks = {r: {1: DocChunk(chunk_no=1, heading="H", text=f"text of {r}", text_hash=hashlib.sha256(r.encode()).hexdigest())} for r in (ARCH, TEAMS)}
    assert [e.entity_id for e in neighbours(ENGINE, [ENGINE, INDEX, TEAM])] == ["DataStore/search-index", "Team/matching-team"]
    picked = gather(ENGINE, [ENGINE, INDEX, TEAM], lambda r: chunks[r])  # the index's chunk 2 does not exist here: skipped
    assert [(r, c.chunk_no) for r, c in picked] == [(ARCH, 1), (TEAMS, 1)]
    assert evidence_text(picked).startswith("[arch.md, chunk 1] H\ntext of")
    assert evidence_lines(picked, ENGINE) == ["arch.md: H (chunk 1)"]


def test_one_item_per_entity_with_code_set_fields_and_neighbour_evidence(tmp_bundle):
    setup_graph()
    agent, client = extractor(submit({"technology": "Python 3.12", "owner": "Matching Team"}, "The engine."),
                              submit({"technology": "OpenSearch 2.13"}))
    reports = extract_entity_items("App", agent)
    assert [(r.entity, r.outcome) for r in reports] == [("Architecture", ExtractionOutcome.SAVED)]
    first = client.requests[0][1][0].text
    assert "Item: Matching Engine (also: AI Engine)" in first and "[teams.md, chunk 1]" in first  # the owner is stated in the teams document
    schema = client.requests[0][2][0].input_schema_json
    assert '"technology"' in schema and '"evidence"' not in schema and '"relations"' not in schema and '"name"' not in schema
    item = item_json(KEY, ENGINE.entity_id)["components"][0]
    assert item["name"] == "Matching Engine" and item["technology"] == "Python 3.12" and item["owner"] == "Matching Team"
    assert item["dependencies"] == ["Search Index"] and item["evidence"] == ["arch.md: Matching Engine (chunk 1)"]
    assert {(r["target"], r["kind"]) for r in item["relations"]} == {("Search Index", "depends_on"), ("Matching Team", "relates_to")}
    fact = json.loads(BundleStore().read_fact(KEY).value)
    assert [c["name"] for c in fact["components"]] == ["Matching Engine"] and [d["name"] for d in fact["data_stores"]] == ["Search Index"]
    assert {s.resource for s in BundleStore().read_fact(KEY).sources} == {ARCH}


def test_unchanged_entities_make_no_call_and_removed_entities_lose_their_item(tmp_bundle):
    setup_graph()
    extract_entity_items("App", extractor(submit({"technology": "Python"}), submit({}))[0])
    agent, client = extractor()
    assert [r.outcome for r in extract_entity_items("App", agent)] == [ExtractionOutcome.SKIPPED_UNCHANGED_CHUNKS] and client.requests == []
    EntityStore().write_all("App", [INDEX, TEAM], "2026-10-03T00:00:00Z")
    extract_entity_items("App", extractor()[0])
    assert item_json(KEY, ENGINE.entity_id) is None
    assert [c["name"] for c in json.loads(BundleStore().read_fact(KEY).value).get("components", [])] == []


def test_entity_items_replace_the_list_items_of_file_contributions(tmp_bundle):
    setup_graph()
    junk = {"components": [{"name": "Firewalls"}, {"name": "Matching Engine", "purpose": "Ranks."}], "architecture_style": "Microservices"}
    ContributionStore().save(KEY, ARCH, junk, None, None, "old/1", "2026-10-01T00:00:00Z")
    extract_entity_items("App", extractor(submit({"technology": "Python"}), submit({}))[0])
    fact = json.loads(BundleStore().read_fact(KEY).value)
    assert [c["name"] for c in fact["components"]] == ["Matching Engine"] and fact["components"][0]["purpose"] == ""
    assert fact["architecture_style"] == "Microservices"  # fact-level fields still come from the files


def test_an_item_missing_a_mandatory_field_is_not_stored(tmp_bundle):
    kpi = EntityRecord(entity_id="Kpi/placements", scope="Shared", type="Kpi", name="Placements", evidence=[ev("Shared/references/kpi.md", 1)])
    store("Shared/references/kpi.md", [("KPIs", "Placements per month are tracked.")])
    EntityStore().write_all("Shared", [kpi], "2026-10-02T00:00:00Z")
    reports = extract_entity_items("Shared", extractor(submit({}))[0])
    assert any("not a valid Kpi yet (definition)" in note for note in reports[0].batch_notes)
    assert not (bundle_root() / contribution_relpath("Shared.Kpis", entity_resource(kpi.entity_id))).exists()


def test_a_failed_call_is_reported_and_retried_next_time(tmp_bundle):
    setup_graph((INDEX,))
    reports = extract_entity_items("App", extractor([ModelResponse(text=""), ModelResponse(text="")])[0])
    assert reports[0].failed_batches == 1 and item_json(KEY, INDEX.entity_id) is None
    assert extract_entity_items("App", extractor(submit({"technology": "OpenSearch"}))[0])[0].batches == 1
