"""Discovery: chunks that no entity claims are kept as notes (redesign step 4), tested with a scripted model."""
import json

import pytest
from pydantic import ValidationError

from docfactory import clock
from docfactory.agents.discoverer import Discoverer
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.contribution_store import ContributionStore
from docfactory.bundle.paths import bundle_root
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.coverage import file_coverage
from docfactory.extract.discovery_pipeline import discover_file
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.coverage_status import CoverageStatus
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.model_response import ModelResponse
from docfactory.models.note_draft import NoteDraft
from docfactory.models.tool_call import ToolCall
from docfactory.tools.discovery_tools import DISCOVERY_TOOL_NAMES, discovery_errors, discovery_package, in_text

APP = "Acme/references/srs.md"
TEXTS = ["Acme SRS cover page, version 0.3.", "FR-01. The system SHALL log in.", "Open issue 1: the payment provider is not chosen yet.", "Page 3 of 9"]
KEY = "Acme.Note"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-04T10:00:00Z")


def store(path=APP, tagged=(2,)):
    original = bundle_root() / path
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("".join(f"## Section {n}\n{t}\n\n" for n, t in enumerate(TEXTS, 1)), encoding="utf-8")
    chunks = chunk_file(original)
    tags = [ChunkTag(chunk_no=n, entity="FunctionalRequirements", origin="rule", score=4, evidence="t") for n in tagged]
    SourceStore().write(path, file_sha256(original), "2026-10-01T00:00:00Z", chunks, tags)


def answer(notes, nothing=None):
    arguments = {"notes": notes} | ({"nothing_to_keep": nothing} if nothing is not None else {})
    return [ModelResponse(tool_calls=[ToolCall(id="c", name="submit_discovery", arguments_json=json.dumps(arguments))]), ModelResponse(text="done")]


def discoverer(*answers):
    client = FakeModelClient([r for a in answers for r in a])
    client.model = "fake"
    return Discoverer(client, system="S")


COVER = {"title": "Cover page", "summary": "Names the document.", "statements": ["Acme SRS cover page, version 0.3."], "kind": "cover page", "chunks": [1]}
ISSUES = {"title": "Open issues", "summary": "One open issue.", "statements": ["Open issue 1: the payment provider is not chosen yet."], "chunks": [3]}


def full_answer():
    return answer([COVER, ISSUES], [4])


def test_the_package_holds_exactly_one_tool():
    assert DISCOVERY_TOOL_NAMES == ["submit_discovery"]
    package = discovery_package({1}, "text", [])
    assert [t.name for t in package.tools()] == ["submit_discovery"] and package.name == "discovery"


def test_the_tool_checks_the_answer_and_appends_an_accepted_one():
    accepted = []
    package = discovery_package({1, 2}, "[chunk 1] Cover\nAcme cover page.\n[chunk 2] X\nPage 2", accepted)
    refused = package.call("submit_discovery", {"notes": [{"title": "Cover", "summary": "s", "chunks": [1]}]})
    assert refused["ok"] is False and "chunks [2] are in no note" in refused["errors"][0] and accepted == []
    ok = package.call("submit_discovery", {"notes": [{"title": "Cover", "summary": "s", "chunks": [1]}], "nothing_to_keep": [2]})
    assert ok == {"ok": True, "notes": 1} and accepted[0][1] == [2] and accepted[0][0][0].title == "Cover"


def test_discovery_errors_name_every_kind_of_problem():
    note = NoteDraft(title="A", summary="s", chunks=[1])
    text = "Cover page text."
    assert discovery_errors([note], [], {1}, text) == []
    assert "not given to you" in discovery_errors([NoteDraft(title="A", summary="s", chunks=[9])], [], {1}, text)[0]
    assert any("share the title" in e for e in discovery_errors([note, note], [], {1}, text))
    assert any("neither a summary nor statements" in e for e in discovery_errors([NoteDraft(title="A", chunks=[1])], [], {1}, text))
    assert any("not in the chunks" in e for e in discovery_errors([NoteDraft(title="A", statements=["Completely invented budget figure"], chunks=[1])], [], {1}, text))
    assert any("both in a note" in e for e in discovery_errors([note], [1], {1}, text))
    assert in_text("cover page", text) and not in_text("quarterly revenue projections exceed expectations", text)
    with pytest.raises(ValidationError):
        NoteDraft(title="A", chunks=[])


def test_unclaimed_chunks_become_notes_with_their_sources(tmp_bundle):
    store()
    report = discover_file(APP, discoverer(full_answer()))
    assert (report.entity, report.outcome, report.key, report.items, report.chunks_used) == ("Note", ExtractionOutcome.SAVED, KEY, 2, 3)
    fact = json.loads(BundleStore().read_fact(KEY).value)
    assert [n["title"] for n in fact["notes"]] == ["Cover page", "Open issues"]
    assert fact["notes"][0]["source_chunks"] == [f"{APP}#1"] and fact["notes"][0]["kind"] == "cover page"
    assert BundleStore().read_fact(KEY).generated_by == "okf-discovery-agent/fake"
    assert [i.item_id for i in BundleStore().list_items(KEY)] == ["Cover page", "Open issues"]


def test_coverage_marks_noted_chunks_and_a_rerun_makes_no_call(tmp_bundle):
    store()
    discover_file(APP, discoverer(full_answer()))
    rows = {c.chunk_no: c.status for c in file_coverage(APP).chunks}
    assert rows == {1: CoverageStatus.NOTED, 2: CoverageStatus.NOT_EXTRACTED, 3: CoverageStatus.NOTED, 4: CoverageStatus.UNMAPPED}
    again = discover_file(APP, discoverer())  # no scripted answers: a call would fail
    assert again.outcome == ExtractionOutcome.SKIPPED_UNCHANGED_CHUNKS and again.reason.startswith("the chunks that are in no fact are unchanged")


def test_a_batch_that_fails_is_reported_and_retried_next_run(tmp_bundle):
    store()
    report = discover_file(APP, discoverer(answer([{"title": "Cover", "summary": "s", "chunks": [9]}])))  # chunk 9 was never given: refused, then no answers left
    assert report.failed_batches >= 1 and report.outcome == ExtractionOutcome.FAILED
    assert ContributionStore().get(KEY, APP) is None


def test_no_notes_worth_keeping_stores_nothing_visible(tmp_bundle):
    store()
    report = discover_file(APP, discoverer(answer([], [1, 3, 4])))
    assert report.outcome == ExtractionOutcome.UNCHANGED and BundleStore().read_fact(KEY) is None
    assert ContributionStore().get(KEY, APP).chunks_hash is not None  # remembered, so the next run asks nothing


def test_when_every_chunk_is_in_a_fact_the_notes_of_the_file_are_removed(tmp_bundle):
    store()
    discover_file(APP, discoverer(full_answer()))
    store(tagged=(1, 2, 3, 4))  # the file now tags every chunk with an entity... not extracted, but claimed
    report = discover_file(APP, discoverer())
    assert report.outcome == ExtractionOutcome.REMOVED and report.entity == "Note"
    assert ContributionStore().get(KEY, APP) is None


def test_files_in_shared_and_general_get_no_notes(tmp_bundle):
    store("general/references/guide.md")
    assert discover_file("general/references/guide.md", discoverer()).outcome == ExtractionOutcome.SKIPPED_SCOPE
    with pytest.raises(FileNotFoundError):
        discover_file("Acme/references/missing.md", discoverer())


def test_the_discoverer_returns_the_accepted_answer_or_what_went_wrong(tmp_bundle):
    store()
    _, chunks = __import__("docfactory.ingest.source_reads", fromlist=["read_chunks"]).read_chunks(APP)
    accepted, note = discoverer(full_answer()).discover_batch(APP, [c for c in chunks if c.chunk_no != 2])
    assert note == "" and [n.title for n in accepted[0]] == ["Cover page", "Open issues"] and accepted[1] == [4]
    none, why = discoverer([ModelResponse(text="I have nothing to submit")]).discover_batch(APP, chunks[:1])
    assert none is None and "without an accepted" in why
