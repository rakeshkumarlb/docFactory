"""Extraction of one DocStore file into facts with a scripted model (Phase 3 redesign, step 2)."""
import json

import pytest

from docfactory import bundle, clock, contributions, db, facts
from docfactory.agents.entity_extractor import EntityExtractor
from docfactory.agents.fake_model_client import FakeModelClient
from docfactory.canonical import sha256_hex
from docfactory.entitysaver.functional_requirements_saver import FunctionalRequirementsSaver
from docfactory.extract.extraction_pipeline import extract_file, format_reports
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.models.model_response import ModelResponse
from docfactory.models.save_action import SaveAction
from docfactory.models.tool_call import ToolCall

A, B = "Acme/srs-a.pdf", "Acme/srs-b.pdf"
FR = "Acme.FunctionalRequirements"
PAD = " Lorem ipsum." * 280  # about 3600 characters: two such chunks do not fit one batch


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-04T10:00:00Z")


def store(path, chunks, timestamp="2026-10-01T00:00:00Z"):
    """Commit a DocStore file with chunks given as (chunk_no, text, entities)."""
    rows = [(no, f"3. Features > 3.{no}", None, None, text, sha256_hex(text)) for no, text, _ in chunks]
    tags = [(no, entity, "rule", 4, "test") for no, _, entities in chunks for entity in entities]
    db.commit_ingested(path, sha256_hex(repr(chunks)), timestamp, rows, tags)


def req(id, title=None):
    return {"id": id, "title": title or f"Title {id}", "description": f"The system SHALL do {id}."}


def text_of(*ids):
    return " ".join(f"{i}. | Title {i} | The system SHALL do {i}." for i in ids)


def submit(values, summary=None):
    arguments = {"values": values} | ({"summary": summary} if summary else {})
    return [ModelResponse(tool_calls=[ToolCall(id="c", name="submit_extraction", arguments_json=json.dumps(arguments))]), ModelResponse(text="done")]


def extractor(*batches):
    client = FakeModelClient([response for batch in batches for response in batch])
    client.model = "fake"
    return EntityExtractor(client, system="S")


def run(path, *batches, **kwargs):
    reports = extract_file(path, extractor(*batches), **kwargs)
    return {r.entity: r for r in reports}


def ids(key=FR):
    return [r["id"] for r in json.loads(facts.get_fact(key).value)["requirements"]]


def test_a_new_file_is_extracted_in_batches_merged_and_saved(tmp_db):
    store(A, [(1, text_of("FR-01") + PAD, ["FunctionalRequirements"]), (2, text_of("FR-02") + PAD, ["FunctionalRequirements"])])
    report = run(A, submit({"requirements": [req("FR-01")]}, "Login."), submit({"requirements": [req("FR-02")]}))["FunctionalRequirements"]
    assert (report.outcome, report.action, report.version, report.batches, report.items) == (ExtractionOutcome.SAVED, SaveAction.CREATED, 1, 2, 2)
    fact = facts.get_fact(FR)
    assert ids() == ["FR-01", "FR-02"] and fact.generated_by == "okf-extraction-agent/fake" and fact.status.value == "draft"
    assert f'resource: "{A}"' in fact.frontmatter and '"Login."' in fact.frontmatter
    assert (bundle.bundles_root() / fact.file_path.removeprefix("bundles/")).exists()
    assert contributions.get_contribution(FR, A).chunks_hash is not None
    assert any(q.startswith("summary:") for q in report.missing_questions)


def test_unchanged_chunks_are_skipped_without_any_llm_call(tmp_db):
    store(A, [(1, text_of("FR-01"), ["FunctionalRequirements"])])
    run(A, submit({"requirements": [req("FR-01")]}))
    report = run(A)["FunctionalRequirements"]  # the fake client has no responses: any call would fail the test
    assert report.outcome == ExtractionOutcome.SKIPPED_UNCHANGED_CHUNKS and report.contributions == 1
    assert run(A, submit({"requirements": [req("FR-01")]}), force=True)["FunctionalRequirements"].outcome == ExtractionOutcome.UNCHANGED


def test_two_files_merge_newest_first_with_conflicts_reported(tmp_db):
    store(A, [(1, text_of("FR-01", "FR-02"), ["FunctionalRequirements"])], timestamp="2026-10-01T00:00:00Z")
    store(B, [(1, text_of("FR-02", "FR-03"), ["FunctionalRequirements"])], timestamp="2026-10-02T00:00:00Z")
    run(A, submit({"requirements": [req("FR-01"), req("FR-02", "Old title")]}))
    report = run(B, submit({"requirements": [req("FR-02", "New title"), req("FR-03")]}))["FunctionalRequirements"]
    assert ids() == ["FR-02", "FR-03", "FR-01"] and report.contributions == 2 and report.version == 2
    assert report.conflicts == [f"requirements[FR-02].title: kept 'New title' from {B}; {A} says 'Old title'"]
    frontmatter = facts.get_fact(FR).frontmatter
    assert A in frontmatter and B in frontmatter


def test_a_changed_file_replaces_only_its_own_contribution(tmp_db):
    store(A, [(1, text_of("FR-01", "FR-02"), ["FunctionalRequirements"])])
    store(B, [(1, text_of("FR-03"), ["FunctionalRequirements"])], timestamp="2026-10-02T00:00:00Z")
    run(A, submit({"requirements": [req("FR-01"), req("FR-02")]}))
    run(B, submit({"requirements": [req("FR-03")]}))
    store(A, [(1, text_of("FR-01"), ["FunctionalRequirements"])], timestamp="2026-10-03T00:00:00Z")  # FR-02 removed from A
    report = run(A, submit({"requirements": [req("FR-01")]}))["FunctionalRequirements"]
    assert ids() == ["FR-01", "FR-03"] and report.version == 3


def test_an_entity_no_longer_tagged_loses_the_files_contribution(tmp_db):
    store(A, [(1, text_of("FR-01"), ["FunctionalRequirements"])])
    store(B, [(1, text_of("FR-03"), ["FunctionalRequirements"])], timestamp="2026-10-02T00:00:00Z")
    run(A, submit({"requirements": [req("FR-01")]}))
    run(B, submit({"requirements": [req("FR-03")]}))
    store(A, [(1, "Nothing about requirements any more.", [])], timestamp="2026-10-03T00:00:00Z")
    report = run(A)["FunctionalRequirements"]
    assert report.outcome == ExtractionOutcome.REMOVED and report.contributions == 1 and ids() == ["FR-03"]
    assert contributions.get_contribution(FR, A) is None


def test_a_rejected_fact_keeps_the_contribution_for_a_later_file(tmp_db):
    store(A, [(1, "Recruiters and job seekers use it.", ["ApplicationOverview"])])
    store(B, [(1, "Acme matches jobs to people.", ["ApplicationOverview"])], timestamp="2026-10-02T00:00:00Z")
    first = run(A, submit({"target_users": ["Recruiters", "Job seekers"]}))["ApplicationOverview"]
    assert first.outcome == ExtractionOutcome.REJECTED and {e.path for e in first.save_errors} == {"application_name", "purpose"}
    assert facts.get_fact("Acme.ApplicationOverview") is None and contributions.get_contribution("Acme.ApplicationOverview", A)
    second = run(B, submit({"application_name": "Acme", "purpose": "Acme matches jobs to people."}))["ApplicationOverview"]
    assert second.outcome == ExtractionOutcome.SAVED
    assert json.loads(facts.get_fact("Acme.ApplicationOverview").value)["target_users"] == ["Recruiters", "Job seekers"]


def test_shared_entities_in_an_application_document_and_general_files_are_skipped(tmp_db):
    store(A, [(1, "Availability 99.9%.", ["Slo"])])
    store("general/notes.txt", [(1, text_of("FR-01"), ["FunctionalRequirements"])])
    assert run(A)["Slo"].outcome == ExtractionOutcome.SKIPPED_SCOPE
    assert run("general/notes.txt")["FunctionalRequirements"].outcome == ExtractionOutcome.SKIPPED_SCOPE
    assert facts.list_facts() == []


def test_a_failed_batch_does_not_stop_the_others_and_is_retried_next_run(tmp_db):
    store(A, [(1, text_of("FR-01") + PAD, ["FunctionalRequirements"]), (2, text_of("FR-02") + PAD, ["FunctionalRequirements"])])
    report = run(A, [ModelResponse(text=""), ModelResponse(text="")], submit({"requirements": [req("FR-02")]}))["FunctionalRequirements"]
    assert (report.outcome, report.failed_batches, ids()) == (ExtractionOutcome.SAVED, 1, ["FR-02"])
    assert report.batch_notes[0].startswith("chunks 1-1:")
    assert contributions.get_contribution(FR, A).chunks_hash is None  # not skipped next time
    again = run(A, submit({"requirements": [req("FR-01")]}), submit({"requirements": [req("FR-02")]}))["FunctionalRequirements"]
    assert again.outcome == ExtractionOutcome.SAVED and ids() == ["FR-01", "FR-02"]


def test_a_failed_batch_of_several_chunks_is_split_and_retried(tmp_db):
    store(A, [(1, text_of("FR-01"), ["FunctionalRequirements"]), (2, text_of("FR-02"), ["FunctionalRequirements"])])  # one batch
    report = run(A, [ModelResponse(text=""), ModelResponse(text="")], submit({"requirements": [req("FR-01")]}),
                 submit({"requirements": [req("FR-02")]}))["FunctionalRequirements"]
    assert (report.outcome, report.batches, report.failed_batches, ids()) == (ExtractionOutcome.SAVED, 3, 0, ["FR-01", "FR-02"])
    assert "split and retried" in report.batch_notes[0]
    assert contributions.get_contribution(FR, A).chunks_hash is not None  # complete after the retry


def test_all_batches_failing_stores_nothing(tmp_db):
    store(A, [(1, text_of("FR-01"), ["FunctionalRequirements"])])
    report = run(A, [ModelResponse(text="no tool")])["FunctionalRequirements"]
    assert report.outcome == ExtractionOutcome.FAILED and facts.get_fact(FR) is None and contributions.list_contributions() == []


def test_a_fact_stored_before_extraction_is_kept_as_the_lowest_contribution(tmp_db):
    FunctionalRequirementsSaver().save(FR, {"requirements": [req("FR-00")]})
    store(A, [(1, text_of("FR-01"), ["FunctionalRequirements"])])
    run(A, submit({"requirements": [req("FR-01")]}))
    assert ids() == ["FR-01", "FR-00"]
    assert [c.resource for c in contributions.list_contributions(FR)] == [contributions.EXISTING, A]


def test_ungrounded_values_are_reported(tmp_db):
    store(A, [(1, text_of("FR-01"), ["FunctionalRequirements"])])
    report = run(A, submit({"summary": "Payroll and invoicing for hospitals", "requirements": [req("FR-01")]}))["FunctionalRequirements"]
    assert report.ungrounded_values == ["summary: 'Payroll and invoicing for hospitals'"]


def test_entity_filter_unknown_entity_and_missing_file(tmp_db):
    store(A, [(1, text_of("FR-01"), ["FunctionalRequirements"]), (2, "Python and SQLite.", ["Architecture"])])
    assert set(run(A, submit({"requirements": [req("FR-01")]}), entities=["FunctionalRequirements"])) == {"FunctionalRequirements"}
    with pytest.raises(ValueError):
        extract_file(A, extractor(), entities=["Nope"])
    with pytest.raises(FileNotFoundError):
        extract_file("Acme/missing.pdf", extractor())


def test_format_reports_lists_each_entity(tmp_db):
    store(A, [(1, text_of("FR-01"), ["FunctionalRequirements"]), (2, "Availability.", ["Slo"])])
    text = format_reports(A, extract_file(A, extractor(submit({"requirements": [req("FR-01")]}))))
    assert f"FunctionalRequirements: SAVED -> {FR} v1" in text and "Slo: SKIPPED_SCOPE" in text and "still missing" in text


def test_empty_priorities_are_filled_from_keywords_and_counted(tmp_db):
    store(A, [(1, text_of("FR-01", "FR-02"), ["FunctionalRequirements"])])
    report = run(A, submit({"requirements": [req("FR-01"), {**req("FR-02"), "priority": "COULD"}]}))["FunctionalRequirements"]
    priorities = [r.get("priority") for r in json.loads(facts.get_fact(FR).value)["requirements"]]
    assert priorities == ["MUST", "COULD"] and report.priorities_from_keywords == 1
