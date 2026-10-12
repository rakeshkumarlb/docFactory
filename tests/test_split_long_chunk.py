"""A single long chunk whose answer the model cannot deliver is cut in two and retried."""
import json

from docfactory.agents.entity_extractor import EntityExtractor
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.paths import bundle_root
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.batching import split_chunk
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.models.chunk_tag import ChunkTag
from docfactory.extract.extraction_pipeline import extract_file
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.model_response import ModelResponse
from docfactory.models.tool_call import ToolCall
from test_extraction_pipeline import A, FR

TABLE = "ID | Title | Statement\n" + "\n".join(f"FR-{n:02d} | Title {n} | The system SHALL do {n}." for n in range(1, 9))


def chunk(text):
    return DocChunk(chunk_no=3, heading="3. Components", text=text, text_hash="0" * 64)


def test_a_table_is_cut_in_the_middle_and_the_second_half_repeats_the_header():
    first, second = split_chunk(chunk(TABLE))
    assert first.text.splitlines()[0] == second.text.splitlines()[0] == "ID | Title | Statement"
    assert first.text.splitlines()[1] == "FR-01 | Title 1 | The system SHALL do 1."
    assert second.text.splitlines()[-1].startswith("FR-08") and (first.chunk_no, first.heading) == (second.chunk_no, second.heading) == (3, "3. Components")
    rows = [l for l in first.text.splitlines()[1:] + second.text.splitlines()[1:]]
    assert len(rows) == 8 and len(set(rows)) == 8  # every row is in exactly one half


def test_plain_text_is_cut_without_a_header_and_a_short_chunk_is_not_cut():
    first, second = split_chunk(chunk("one\ntwo\nthree\nfour\nfive"))
    assert (first.text, second.text) == ("one\ntwo", "three\nfour\nfive")
    short = chunk("a\nb\nc")
    assert split_chunk(short) == [short]


def empty():
    return [ModelResponse(text=""), ModelResponse(text="")]  # the model returned neither a tool call nor text, twice


def submit(*ids):
    values = {"requirements": [{"id": i, "title": f"Title {i}", "description": f"The system SHALL do {i}."} for i in ids]}
    return [ModelResponse(tool_calls=[ToolCall(id="c", name="submit_extraction", arguments_json=json.dumps({"values": values}))]), ModelResponse(text="done")]


def test_the_pipeline_retries_the_halves_of_a_chunk_the_model_could_not_answer(tmp_bundle):
    original = bundle_root() / A
    original.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"| FR-{n:02d} | Title {n} | The system SHALL do {n}. |" for n in range(1, 7))
    original.write_text(f"## Section 1\n| ID | Title | Statement |\n|---|---|---|\n{rows}\n", encoding="utf-8")
    chunks = chunk_file(original)
    assert len(chunks) == 1 and len(chunks[0].text.splitlines()) == 7
    SourceStore().write(A, file_sha256(original), "2026-10-01T00:00:00Z", chunks, [ChunkTag(chunk_no=1, entity="FunctionalRequirements", origin="rule", score=4, evidence="t")])
    client = FakeModelClient(empty() + submit("FR-01", "FR-02") + submit("FR-03", "FR-04", "FR-05", "FR-06"))
    client.model = "fake"
    report = {r.entity: r for r in extract_file(A, EntityExtractor(client, system="S"))}["FunctionalRequirements"]
    assert report.outcome == ExtractionOutcome.SAVED and report.failed_batches == 0 and report.items == 6
    assert any("cut in two and retried" in n for n in report.batch_notes)
    assert [r["id"] for r in json.loads(BundleStore().read_fact(FR).value)["requirements"]] == ["FR-01", "FR-02", "FR-03", "FR-04", "FR-05", "FR-06"]
