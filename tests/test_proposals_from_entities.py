"""Type proposals from recurring proposed types of the entity graph: threshold, closeness to existing entities, unchanged evidence."""
import json

import pytest

from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.agents.type_proposer import TypeProposer
from docfactory.bundle.entity_store import EntityStore
from docfactory.bundle.paths import bundle_root
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.proposal_pipeline import propose_from_entities
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.models.entity_evidence import EntityEvidence
from docfactory.models.entity_record import EntityRecord
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall

DOC = "App/references/certs.md"


@pytest.fixture(autouse=True)
def tmp_staging(tmp_bundle, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_STAGING", str(tmp_bundle / "staging"))  # proposals live in staging/: never the repo's


def setup(names, type_="proposed:Certificate"):
    original = bundle_root() / DOC
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("".join(f"## {n}\nThe {n} certificate expires yearly.\n\n" for n in names), encoding="utf-8")
    SourceStore().write(DOC, file_sha256(original), "2026-10-01T00:00:00Z", chunk_file(original), [])
    entities = [EntityRecord(entity_id=f"Proposed-Certificate/c{i}", scope="App", type=type_, name=n, summary=f"The {n} certificate.",
                             evidence=[EntityEvidence(resource=DOC, chunk_no=i + 1)]) for i, n in enumerate(names)]
    EntityStore().write_all("App", entities, "2026-10-02T00:00:00Z")


def proposer(*answers):
    responses = []
    for proposals in answers:
        responses += [ModelResponse(tool_calls=[ToolCall(id="c", name="submit_type_proposal", arguments_json=json.dumps({"proposals": proposals}))]),
                      ModelResponse(text="done")]
    client = FakeModelClient(responses)
    client.model = "fake"
    return TypeProposer(client, system="S"), client


def test_a_type_below_the_threshold_is_not_asked(tmp_bundle):
    setup(["Web TLS", "API TLS"])  # two entities, one file
    agent, client = proposer()
    assert propose_from_entities("App", agent) == [] and client.requests == []


def test_a_recurring_type_is_asked_once_with_its_examples(tmp_bundle):
    setup(["Web TLS", "API TLS", "Mail TLS"])
    agent, client = proposer([])
    reports = propose_from_entities("App", agent)
    assert [r.path for r in reports] == ["(entities) App Certificate"] and reports[0].reason == "the proposer drafted no new type"
    message = client.requests[0][1][0].text
    assert "Certificate (3 found in 1 documents)" in message and "- Web TLS: The Web TLS certificate." in message
    agent, client = proposer()
    assert "unchanged" in propose_from_entities("App", agent)[0].reason and client.requests == []


def test_a_type_close_to_an_existing_entity_is_not_proposed(tmp_bundle):
    setup(["A", "B", "C"], type_="proposed:Environment")
    agent, client = proposer()
    reports = propose_from_entities("App", agent)
    assert "close to Environments" in reports[0].reason and client.requests == []
