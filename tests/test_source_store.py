"""Source concepts (one per ingested original) and the reads built on them (Step 3 of the OKF bundle redesign)."""
import json

import pytest

from docfactory.agents.entity_extractor import EntityExtractor
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.bundle import paths
from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.source_file_parse import parse_source_file
from docfactory.bundle.source_file_render import render_source_file
from docfactory.bundle.source_store import SourceStore
from docfactory.canonical import sha256_hex
from docfactory.extract.extraction_pipeline import extract_file
from docfactory.ingest import pipeline, source_reads
from docfactory.ingest.chunks_out_of_date_error import ChunksOutOfDateError
from docfactory.ingest.paths import INCOMING_ENV, STAGING_ENV
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall

RESOURCE = "Acme/references/srs.md"
SRS = "# Acme Software Requirements Specification\n\n## 3. Functional Requirements\n| ID | Requirement |\n|---|---|\n| FR-01 | The system SHALL let users book a room. |\n"


@pytest.fixture
def store(tmp_bundle):
    return SourceStore()


def _chunk(no, text):
    return DocChunk(chunk_no=no, heading=f"Spec > {no}. Heading, with \"quotes\": and colons", text=text, text_hash=sha256_hex(text))


def _tag(no, entity="FunctionalRequirements", origin="rule"):
    return ChunkTag(chunk_no=no, entity=entity, origin=origin, score=6, evidence="heading 'functional requirements'; ids FR-01..FR-02")


def test_a_source_round_trips_through_its_file_with_awkward_text(store):
    version, before = store.write(RESOURCE, sha256_hex("v1"), "2026-10-03T12:00:00+00:00", [_chunk(1, "one"), _chunk(2, "two")], [_tag(2), _tag(1, "Slo", "llm/m:1")])
    assert (version, before) == (1, None)
    record = store.read(RESOURCE)
    assert (record.path, record.version, record.timestamp) == (RESOURCE, 1, "2026-10-03T12:00:00+00:00")
    assert [(c.chunk_no, c.heading, c.text_hash) for c in record.chunks] == [(1, _chunk(1, "one").heading, sha256_hex("one")), (2, _chunk(2, "two").heading, sha256_hex("two"))]
    assert [(t.chunk_no, t.entity, t.origin, t.score, t.evidence) for t in record.tags] == [(2, "FunctionalRequirements", "rule", 6, _tag(2).evidence), (1, "Slo", "llm/m:1", 6, _tag(1).evidence)]
    assert parse_source_file(render_source_file(record)) == record


def test_same_hash_keeps_the_version_and_another_hash_adds_one(store):
    store.write(RESOURCE, sha256_hex("v1"), "2026-10-03T12:00:00+00:00", [_chunk(1, "one")], [_tag(1)])
    assert store.write(RESOURCE, sha256_hex("v1"), "2026-10-03T12:00:00+00:00", [_chunk(1, "one")], [])[0] == 1  # a repair or re-tag
    version, before = store.write(RESOURCE, sha256_hex("v2"), "2026-10-04T12:00:00+00:00", [_chunk(1, "one")], [_tag(1)])
    assert (version, before.version) == (2, 1)
    assert store.read(RESOURCE).version == 2


def test_find_by_name_and_hash_list_by_scope_and_a_missing_source_is_none(store):
    store.write("A/references/x.md", sha256_hex("a"), "t", [], [])
    store.write("B/references/x.md", sha256_hex("b"), "t", [], [])
    store.write("B/references/y.md", sha256_hex("a"), "t", [], [])
    assert [r.path for r in store.find(file_name="x.md")] == ["A/references/x.md", "B/references/x.md"]
    assert [r.path for r in store.find(hashcode=sha256_hex("a"))] == ["A/references/x.md", "B/references/y.md"]
    assert [r.path for r in store.list("B")] == ["B/references/x.md", "B/references/y.md"]
    assert store.read("C/references/none.md") is None


def test_a_log_line_is_written_for_a_new_and_for_a_changed_source_but_not_for_a_repair(store):
    store.write(RESOURCE, sha256_hex("v1"), "2026-10-03T12:00:00+00:00", [], [])
    store.write(RESOURCE, sha256_hex("v1"), "2026-10-03T12:00:00+00:00", [], [])
    store.write(RESOURCE, sha256_hex("v2"), "2026-10-04T12:00:00+00:00", [], [])
    log = (store.root / "log.md").read_text(encoding="utf-8")
    assert log.count("Acme/sources/srs.md.md") == 2 and "* **Creation**" in log and "* **Update**" in log


def test_sources_are_not_listed_as_facts_and_facts_are_not_sources(store):
    store.write(RESOURCE, sha256_hex("v1"), "t", [], [])
    BundleStore().write_fact("Acme.ApplicationOverview", {"application_name": "Acme", "purpose": "Books rooms."})
    assert [r.path for r in store.list()] == [RESOURCE]
    assert [r.key for r in BundleStore().list_facts()] == ["Acme.ApplicationOverview"]


def test_a_file_that_is_not_a_source_is_refused(store):
    path = store.root / "Acme" / "sources"
    path.mkdir(parents=True)
    (path / "bad.md.md").write_text("---\ntype: Other\n---\n", encoding="utf-8")
    with pytest.raises(BundleError):
        store.list()


@pytest.mark.parametrize("resource", ["srs.md", "Acme/srs.md", "Acme/sources/srs.md", "Acme/references/"])
def test_a_resource_must_be_scope_references_name(resource):
    with pytest.raises(ValueError):
        paths.source_relpath(resource)


def test_shared_scope_maps_to_the_folder_of_the_shared_facts():
    assert paths.reference_path("shared", "s.pdf") == "Shared/references/s.pdf"
    assert paths.reference_path("Acme", "s.pdf") == "Acme/references/s.pdf"


def _extractor(responses):
    client = FakeModelClient(responses)
    client.model = "fake"
    return EntityExtractor(client, system="S")


@pytest.fixture
def ingested(tmp_bundle, tmp_path, monkeypatch):
    monkeypatch.setenv(INCOMING_ENV, str(tmp_path / "incoming"))
    monkeypatch.setenv(STAGING_ENV, str(tmp_path / "staging"))
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "srs.md").write_text(SRS, encoding="utf-8")
    [report] = pipeline.run_ingest(lambda: "2026-10-03T12:00:00+00:00")
    assert report.target_path == RESOURCE, report
    return SourceStore()


def test_read_chunks_rederives_the_chunks_and_read_source_text_rebuilds_the_document(ingested):
    record, chunks = source_reads.read_chunks(RESOURCE)
    assert [c.chunk_no for c in chunks] == [c.chunk_no for c in record.chunks] and "FR-01" in chunks[0].text
    assert "FR-01" in source_reads.read_source_text(RESOURCE).split("\n\n")[0]
    assert [r.path for r in source_reads.search_sources(name_contains="SRS")] == [RESOURCE]
    assert source_reads.search_sources(folder="Other") == []


def test_an_original_that_no_longer_chunks_as_at_ingestion_is_refused_with_the_fix(ingested):
    ingested.original(RESOURCE).write_text(SRS + "\n## 4. Extra\nMore text.\n", encoding="utf-8")
    with pytest.raises(ChunksOutOfDateError, match="chunk_rebuild"):
        source_reads.read_chunks(RESOURCE)
    with pytest.raises(ChunksOutOfDateError):
        extract_file(RESOURCE, _extractor([]))


def test_a_missing_source_or_original_is_a_file_not_found(ingested):
    with pytest.raises(FileNotFoundError, match="no such file"):
        source_reads.read_chunks("Acme/references/none.md")
    ingested.original(RESOURCE).unlink()
    with pytest.raises(FileNotFoundError, match="missing on disk"):
        source_reads.read_chunks(RESOURCE)


def test_ingest_then_extract_end_to_end_saves_a_fact_sourced_from_the_original(ingested):
    arguments = {"values": {"requirements": [{"id": "FR-01", "title": "Book", "description": "The system SHALL let users book a room."}]}, "summary": "Booking."}
    responses = [ModelResponse(tool_calls=[ToolCall(id="c", name="submit_extraction", arguments_json=json.dumps(arguments))]), ModelResponse(text="done")]
    [report] = [r for r in extract_file(RESOURCE, _extractor(responses)) if r.entity == "FunctionalRequirements"]
    assert report.outcome.value == "SAVED"
    fact = BundleStore().read_fact("Acme.FunctionalRequirements")
    assert [s.resource for s in fact.sources] == [RESOURCE] and fact.sources[0].last_modified == "2026-10-03T12:00:00+00:00"
    contribution = ingested.root / "Acme" / "sources" / "srs.md" / "FunctionalRequirements.md"
    assert contribution.is_file() and (ingested.root / "Acme" / "sources" / "srs.md.md").is_file()  # the Source and its folder of contributions
    assert [r.path for r in ingested.list()] == [RESOURCE]
