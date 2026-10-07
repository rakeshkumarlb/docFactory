"""Phase 4 generate: body, document control, revision history, gaps, needs list and rendering, without an LLM (a fake writer stands in)."""
import json

import pytest

from docfactory import clock, db
from docfactory.documentmodels.documents.srs_document import SrsDocument
from docfactory.documentmodels.shared.document_control import DocumentControl
from docfactory.documentmodels.shared.document_need import DocumentNeed
from docfactory.documentmodels.shared.missing_info import MissingInfo
from docfactory.documentmodels.shared.revision_history import RevisionHistory
from docfactory.documentsaver.shared.document_control_saver import DocumentControlSaver
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.functional_requirements_saver import FunctionalRequirementsSaver
from docfactory.generate import main
from docfactory.generation.generate_document import format_reports, generate
from docfactory.open_questions import open_questions

APP = "TestApp"
PREFIX = f"{APP}.Outputs.SRS"

OVERVIEW = {
    "application_name": "TestApp",
    "purpose": "Does the one thing this test needs.",
    "business_overview": "Supports the test suite.",
    "target_users": ["Testers"],
    "key_capabilities": ["Run tests"],
    "business_criticality": "Tier 1",
    "out_of_scope": ["Payroll processing"],
    "technology_summary": "Test stack.",
}

FR = {
    "requirements": [
        {"id": "FR-01", "title": "Login", "description": "The system SHALL let users log in.", "priority": "MUST",
         "rationale": "Users need accounts.", "acceptance_criteria": ["A user with a valid password is logged in."]},
        {"id": "FR-02", "title": "Logout", "description": "The system SHALL let users log out.", "priority": "MUST"},
    ],
    "out_of_scope": ["Payroll processing"],
}


@pytest.fixture
def env(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-07T10:00:00Z")
    assert ApplicationOverviewSaver().save(f"{APP}.ApplicationOverview", OVERVIEW).ok
    assert FunctionalRequirementsSaver().save(f"{APP}.FunctionalRequirements", FR).ok
    return tmp_path / "output" / APP


def _row(key):
    return db.get_row("DocumentOutputs", key)


def _value(model, key):
    return model.model_validate(json.loads(_row(key)["Value"]))


class CountingWriter:
    """A fake needs writer: one need per pair of gaps, for a 'product owner'; or a failure."""

    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def __call__(self, app_id, doc_name, gaps):
        self.calls += 1
        if self.fail:
            return None, "the model ended without an accepted submit_needs call"
        numbers = [gap.number for gap in gaps]
        return [DocumentNeed(question=f"Question about gaps {numbers[i:i + 2]}", audience="product owner", gaps=numbers[i:i + 2])
                for i in range(0, len(numbers), 2)], ""


def test_a_first_run_writes_all_four_rows_and_both_files_with_facts_missing(env):
    report = generate(APP, "SRS")

    assert report.errors == [] and report.body_action.value == "CREATED"
    control = _value(DocumentControl, f"{PREFIX}.DocumentControl")
    assert control.model_dump() == {
        "document_id": "TestApp-SRS", "title": "TestApp Software Requirements Specification", "document_version": "0.1",
        "status": "Draft", "owner": "docFactory", "approvers": [], "created_date": "2026-10-07", "last_updated_date": "2026-10-07"}
    history = _value(RevisionHistory, f"{PREFIX}.RevisionHistory")
    assert len(history.revisions) == 1 and history.revisions[0].version == "0.1" and history.revisions[0].author == "docFactory"
    assert "TestApp.FunctionalRequirements v1" in history.revisions[0].summary and "Shared.Slo (not available)" in history.revisions[0].summary
    info = _value(MissingInfo, f"{PREFIX}.MissingInfo")
    assert info.needs_origin.value == "no_llm" and len(info.needs) == len(info.gaps) == report.gap_count
    text = (env / "SRS.md").read_text(encoding="utf-8")
    assert text.startswith("# TestApp Software Requirements Specification") and "_Not provided._" in text
    assert (env / "SRS.missing.md").exists()


def test_the_gaps_are_exactly_the_unanswered_part_of_the_bound_fields(env):
    generate(APP, "SRS")
    gaps = _value(MissingInfo, f"{PREFIX}.MissingInfo").gaps

    assert [gap.number for gap in gaps] == list(range(1, len(gaps) + 1))
    fr_fact = FunctionalRequirements.model_validate(FR)
    fr_gaps = {gap.field.removeprefix("functional_requirements.") for gap in gaps if gap.field.startswith("functional_requirements.")}
    assert fr_gaps == {question.path for question in open_questions(fr_fact)}
    rationale = next(gap for gap in gaps if gap.field == "functional_requirements.requirements[].rationale")
    assert (rationale.missing_in, rationale.item_count, rationale.example_items) == (1, 2, ["FR-02 | Logout | The system SHALL let users log out."])
    nfr_fields = set(SrsDocument.model_fields["non_functional_requirements"].annotation.model_fields)
    assert {gap.field for gap in gaps if gap.field.startswith("non_functional")} == {f"non_functional_requirements.{f}" for f in nfr_fields}
    assert {gap.field for gap in gaps if gap.field.startswith("service_levels")} == {"service_levels.objectives", "service_levels.notes"}
    assert not [gap for gap in gaps if gap.field.startswith("application_summary")]


def test_a_second_run_with_unchanged_facts_changes_no_row_and_calls_no_writer(env):
    writer = CountingWriter()
    generate(APP, "SRS", writer)
    keys = [PREFIX, f"{PREFIX}.DocumentControl", f"{PREFIX}.RevisionHistory", f"{PREFIX}.MissingInfo"]
    before = {key: (_row(key)["Version"], _row(key)["Hashcode"]) for key in keys}

    report = generate(APP, "SRS", writer)

    assert {key: (_row(key)["Version"], _row(key)["Hashcode"]) for key in keys} == before
    assert writer.calls == 1 and report.needs_skipped and report.revision_added == "" and report.output_files == []


def test_a_changed_fact_adds_one_revision_naming_the_changed_section(env, monkeypatch):
    generate(APP, "SRS")
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-09T10:00:00Z")
    assert FunctionalRequirementsSaver().save(f"{APP}.FunctionalRequirements", FR | {"summary": "Log in and out."}).ok

    report = generate(APP, "SRS")

    history = _value(RevisionHistory, f"{PREFIX}.RevisionHistory")
    assert [entry.version for entry in history.revisions] == ["0.1", "0.2"]
    assert history.revisions[1].summary == "Changed sections: functional_requirements (from TestApp.FunctionalRequirements v2)."
    assert history.revisions[1].date == "2026-10-09" and report.revision_added == history.revisions[1].summary
    control = _value(DocumentControl, f"{PREFIX}.DocumentControl")
    assert (control.document_version, control.created_date, control.last_updated_date) == ("0.2", "2026-10-07", "2026-10-09")


def test_status_and_approvers_of_the_stored_control_are_kept(env):
    generate(APP, "SRS")
    stored = _value(DocumentControl, f"{PREFIX}.DocumentControl").model_dump() | {"status": "Approved", "approvers": ["QA Lead"]}
    assert DocumentControlSaver().save(f"{PREFIX}.DocumentControl", stored).ok

    generate(APP, "SRS")

    control = _value(DocumentControl, f"{PREFIX}.DocumentControl")
    assert (control.status, control.approvers, control.owner) == ("Approved", ["QA Lead"], "docFactory")


def test_the_writers_needs_are_saved_and_kept_while_the_gaps_do_not_change(env):
    writer = CountingWriter()
    report = generate(APP, "SRS", writer)
    info = _value(MissingInfo, f"{PREFIX}.MissingInfo")
    assert report.needs_origin == "llm" and info.needs[0].audience == "product owner" and len(info.needs) < len(info.gaps)
    assert "## product owner" in (env / "SRS.missing.md").read_text(encoding="utf-8")

    report = generate(APP, "SRS")  # --no-llm with unchanged gaps keeps the LLM's list
    assert report.needs_skipped and _value(MissingInfo, f"{PREFIX}.MissingInfo").needs_origin.value == "llm"


def test_a_failed_writer_falls_back_to_one_need_per_gap_and_is_retried_next_run(env):
    report = generate(APP, "SRS", CountingWriter(fail=True))
    info = _value(MissingInfo, f"{PREFIX}.MissingInfo")
    assert report.needs_origin == "fallback" and "submit_needs" in report.needs_note and len(info.needs) == len(info.gaps)

    writer = CountingWriter()
    assert generate(APP, "SRS", writer).needs_origin == "llm" and writer.calls == 1


def test_no_gaps_means_no_writer_call_and_no_missing_file(env, monkeypatch):
    from docfactory.generation import generate_document
    monkeypatch.setattr(generate_document, "document_gaps", lambda model, app_id: [])
    writer = CountingWriter()

    report = generate(APP, "SRS", writer)

    assert writer.calls == 0 and report.gap_count == 0 and not (env / "SRS.missing.md").exists()


def test_rendering_is_deterministic_and_the_report_is_readable(env):
    generate(APP, "SRS")
    first = (env / "SRS.md").read_bytes(), (env / "SRS.missing.md").read_bytes()
    (env / "SRS.md").unlink()

    report = generate(APP, "SRS")

    assert ((env / "SRS.md").read_bytes(), (env / "SRS.missing.md").read_bytes()) == first
    assert "needs list:" in format_reports(APP, [report])


def test_the_entry_point(env, capsys):
    assert main(["NoSuchApp", "SRS", "--no-llm"]) == 1
    assert "TestApp" in capsys.readouterr().out
    assert main([APP, "all", "--no-llm"]) == 0
    out = capsys.readouterr().out
    assert all(f"  {doc_type}: body CREATED" in out for doc_type in ("Overview", "SMTD", "SRS", "SOP"))
