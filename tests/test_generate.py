"""Generation from YAML templates: one generic builder, saver set and renderer; the four shipped templates; the generate flow."""
import json
from pathlib import Path

import pytest

from docfactory import clock, db
from docfactory.build import FACT_SPECS
from docfactory.generation import document_store
from docfactory.generation.generate_document import generate_document
from docfactory.generation.render_document import render_document_markdown
from docfactory.generation.template_error import TemplateError
from docfactory.generation.template_loader import list_doc_types, load_template
from docfactory.documentmodels.document_need import DocumentNeed
from docfactory.generate import main
from docfactory.documentmodels.document_control import DocumentControl
from docfactory.documentmodels.missing_info import MissingInfo
from docfactory.documentsaver.document_control_saver import DocumentControlSaver
from docfactory.open_questions import open_questions
from docfactory.render import RenderError
from docfactory.saver_resolution import entity_saver_for

APP = "ReadmeForge"
SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "json"
FULL = {
    "ApplicationOverview": ("application_overview", "readmeforge_full.json"),
    "Architecture": ("architecture", "readmeforge_full.json"),
    "Environments": ("environments", "readmeforge_full.json"),
    "Deployment": ("deployment", "readmeforge_full.json"),
    "Monitoring": ("monitoring", "readmeforge_datadog.json"),
    "BackupRecovery": ("backup_recovery", "readmeforge_full.json"),
    "Support": ("support", "readmeforge_full.json"),
    "KnownErrors": ("known_errors", "readmeforge_full.json"),
    "Sop": ("sop", "readmeforge_datadog_runbooks.json"),
    "FunctionalRequirements": ("functional_requirements", "readmeforge_full.json"),
    "NonFunctionalRequirements": ("non_functional_requirements", "readmeforge_full.json"),
    "Kpis": ("kpis", "shared_devex_kpis_full.json"),
    "Slo": ("slo", "shared_platform_slo_full.json"),
}


class CountingWriter:
    def __init__(self):
        self.calls = 0

    def __call__(self, app_id, doc_name, gaps):
        self.calls += 1
        return [DocumentNeed(question=f"Please answer: {gap.question}", audience="owner", gaps=[gap.number]) for gap in gaps], ""


@pytest.fixture
def env(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-07T10:00:00Z")
    return tmp_path / "output"


def _seed(*names):
    for name in names:
        folder, file = FULL[name]
        payload = json.loads((SAMPLES / folder / file).read_text(encoding="utf-8"))
        key = f"Shared.{name}" if FACT_SPECS[name]["shared"] else f"{APP}.{name}"
        result = entity_saver_for(name)().save(key, payload)
        assert result.ok, result.errors


def _files(output: Path, folder: str) -> dict[str, str]:
    root = output / folder
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(root.glob("*.md"))} if root.exists() else {}


DOC_TYPES = {"Overview": "Application Overview", "SMTD": "Software Maintenance and Transition Document",
             "SRS": "Software Requirements Specification", "SOP": "Standard Operating Procedures"}


def test_the_four_shipped_templates_load_with_their_document_names():
    assert list_doc_types() == sorted(DOC_TYPES)
    for doc_type, name in DOC_TYPES.items():
        assert load_template(doc_type).name == name


@pytest.mark.parametrize("seeded", [list(FULL), ["ApplicationOverview", "FunctionalRequirements"], []], ids=["all-facts", "two-facts", "no-facts"])
def test_every_document_type_generates_with_any_set_of_facts_and_rerenders_the_same_bytes(env, seeded):
    _seed(*seeded)
    for doc_type in DOC_TYPES:
        assert generate_document(APP, doc_type, None).errors == []
    first = _files(env, APP)
    assert first and all(name.startswith(tuple(DOC_TYPES)) for name in first)
    for doc_type in DOC_TYPES:
        assert render_document_markdown(APP, doc_type) == first[f"{doc_type}.md"]


def test_a_first_run_writes_the_four_rows_and_both_files_with_the_documents_control_and_history(env):
    _seed("ApplicationOverview", "FunctionalRequirements")
    report = generate_document(APP, "SRS", None)
    prefix = f"{APP}.Outputs.SRS"

    assert report.errors == [] and report.body_action.value == "CREATED"
    keys = {row["DocumentKey"] for row in db.list_rows("DocumentOutputs")}
    assert keys == {f"{prefix}{part}" for part in ("", ".DocumentControl", ".RevisionHistory", ".MissingInfo")}
    control = document_store.stored_model(DocumentControl, f"{prefix}.DocumentControl")
    assert control.model_dump() == {
        "document_id": "ReadmeForge-SRS", "title": "ReadmeForge Software Requirements Specification", "document_version": "0.1",
        "status": "Draft", "owner": "docFactory", "approvers": [], "created_date": "2026-10-07", "last_updated_date": "2026-10-07"}
    history = json.loads(document_store.stored_row(f"{prefix}.RevisionHistory")["Value"])["revisions"]
    assert len(history) == 1 and history[0]["author"] == "docFactory"
    assert f"{APP}.FunctionalRequirements v1" in history[0]["summary"] and "Shared.Slo (not available)" in history[0]["summary"]
    assert (env / APP / "SRS.missing.md").exists()


def test_the_gaps_are_exactly_the_unanswered_part_of_the_bound_fields(env):
    _seed("ApplicationOverview", "FunctionalRequirements")
    generate_document(APP, "SRS", None)
    gaps = document_store.stored_model(MissingInfo, f"{APP}.Outputs.SRS.MissingInfo").gaps

    assert [gap.number for gap in gaps] == list(range(1, len(gaps) + 1))
    fact = entity_saver_for("FunctionalRequirements").model.model_validate(json.loads(db.get_row("KnowledgeFacts", f"{APP}.FunctionalRequirements")["Value"]))
    prefix = "functional_requirements."
    assert {gap.field.removeprefix(prefix) for gap in gaps if gap.field.startswith(prefix)} == {q.path for q in open_questions(fact)}
    assert not [gap for gap in gaps if gap.field.startswith("application_summary.")]


def test_status_and_approvers_of_the_stored_control_are_kept(env):
    _seed("ApplicationOverview")
    generate_document(APP, "SRS", None)
    key = f"{APP}.Outputs.SRS.DocumentControl"
    stored = document_store.stored_model(DocumentControl, key).model_dump() | {"status": "Approved", "approvers": ["QA Lead"]}
    assert DocumentControlSaver().save(key, stored).ok

    generate_document(APP, "SRS", None)

    control = document_store.stored_model(DocumentControl, key)
    assert (control.status, control.approvers, control.owner) == ("Approved", ["QA Lead"], "docFactory")


def test_a_failed_writer_falls_back_to_one_need_per_gap_and_is_retried_next_run(env):
    _seed("ApplicationOverview")
    failing = lambda app_id, doc_name, gaps: (None, "the model ended without an accepted submit_needs call")  # noqa: E731
    report = generate_document(APP, "SRS", failing)
    info = document_store.stored_model(MissingInfo, f"{APP}.Outputs.SRS.MissingInfo")
    assert report.needs_origin == "fallback" and "submit_needs" in report.needs_note and len(info.needs) == len(info.gaps)

    writer = CountingWriter()
    assert generate_document(APP, "SRS", writer).needs_origin == "llm" and writer.calls == 1


def test_no_gaps_means_no_writer_call_and_no_missing_file(env, monkeypatch):
    from docfactory.generation import generate_document as flow

    _seed("ApplicationOverview")
    monkeypatch.setattr(flow, "template_gaps", lambda template, app_id: [])
    writer = CountingWriter()

    report = generate_document(APP, "SRS", writer)

    assert writer.calls == 0 and report.gap_count == 0 and not (env / APP / "SRS.missing.md").exists()


def test_missing_fact_is_a_gap_and_completeness_counts_answered_fields(env):
    _seed("ApplicationOverview")
    report = generate_document(APP, "SRS", None)
    assert report.gap_count > 0
    body = json.loads(db.get_row("DocumentOutputs", f"{APP}.Outputs.SRS")["Value"])
    fields = [f for s in body["sections"] for f in s["fields"]]
    answered = sum(f["status"] == "answered" for f in fields)
    assert 0 < answered < len(fields)
    assert report.body_completeness == pytest.approx(100 * answered / len(fields))
    assert "_Not provided._" in (env / APP / "SRS.md").read_text(encoding="utf-8")


def test_second_run_changes_nothing_and_makes_no_llm_call(env):
    _seed(*FULL)
    writer = CountingWriter()
    generate_document(APP, "SMTD", writer)
    first_calls = writer.calls
    rows = {r["DocumentKey"]: (r["Hashcode"], r["Version"]) for r in db.list_rows("DocumentOutputs")}
    again = generate_document(APP, "SMTD", writer)
    assert {r["DocumentKey"]: (r["Hashcode"], r["Version"]) for r in db.list_rows("DocumentOutputs")} == rows
    assert again.output_files == [] and writer.calls == first_calls


def test_changed_fact_adds_one_revision_naming_the_section(env):
    _seed("ApplicationOverview", "FunctionalRequirements")
    generate_document(APP, "SRS", None)
    payload = json.loads((SAMPLES / "functional_requirements" / "readmeforge_full.json").read_text(encoding="utf-8"))
    payload["summary"] = "A changed summary."
    assert entity_saver_for("FunctionalRequirements")().save(f"{APP}.FunctionalRequirements", payload).ok
    report = generate_document(APP, "SRS", None)
    assert report.revision_added.startswith("Changed sections: functional_requirements (from ")
    history = document_store.stored_row(f"{APP}.Outputs.SRS.RevisionHistory")
    assert len(json.loads(history["Value"])["revisions"]) == 2


def test_needs_writer_is_used_and_kept_for_unchanged_gaps(env):
    _seed("ApplicationOverview")
    writer = CountingWriter()
    assert generate_document(APP, "SRS", writer).needs_origin == "llm"
    assert writer.calls == 1
    assert generate_document(APP, "SRS", writer).needs_skipped and writer.calls == 1


def test_rendering_without_document_control_fails_clearly(env):
    _seed("ApplicationOverview")
    generate_document(APP, "SRS", None)
    with db.connect() as con:
        con.execute("DELETE FROM DocumentOutputs WHERE DocumentKey LIKE '%.DocumentControl'")
    with pytest.raises(RenderError, match="DocumentControl"):
        render_document_markdown(APP, "SRS")


def test_wrongly_wired_templates_are_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCFACTORY_TEMPLATES", str(tmp_path))

    def write(text):
        (tmp_path / "Bad.yaml").write_text(text, encoding="utf-8")

    head = "doc_type: Bad\nname: Bad document\nsections:\n- id: s\n  title: S\n  fields:\n"
    write(head + "  - binding: Nothing.field\n")
    with pytest.raises(TemplateError, match="unknown entity"):
        load_template("Bad")
    write(head + "  - binding: Sop.nothing\n")
    with pytest.raises(TemplateError, match="no field"):
        load_template("Bad")
    write(head + "  - binding: Sop.notes\n  - binding: Sop.notes\n")
    with pytest.raises(TemplateError, match="more than once"):
        load_template("Bad")
    write(head + "  - binding: Sop.notes\n    render_as: grid\n")
    with pytest.raises(TemplateError):
        load_template("Bad")
    with pytest.raises(TemplateError, match="no template"):
        load_template("Missing")


def test_entry_point_runs_and_refuses_unknown_app(env, capsys):
    _seed("ApplicationOverview")
    assert main([APP, "Overview", "--no-llm"]) == 0
    assert (env / APP / "Overview.md").exists()
    assert main(["Nobody", "all", "--no-llm"]) == 1
    assert "has no knowledge facts" in capsys.readouterr().out


def test_a_history_left_behind_by_an_interrupted_run_catches_up_on_the_next_run(env, monkeypatch):
    from docfactory.generation import generate_document as flow

    _seed("ApplicationOverview", "FunctionalRequirements")
    generate_document(APP, "SRS", None)
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-09T10:00:00Z")
    payload = json.loads((SAMPLES / "functional_requirements" / "readmeforge_full.json").read_text(encoding="utf-8"))
    payload["summary"] = "A changed summary."
    assert entity_saver_for("FunctionalRequirements")().save(f"{APP}.FunctionalRequirements", payload).ok

    class Interrupted:
        def save(self, *args, **kwargs):
            raise RuntimeError("the process stopped")

    with monkeypatch.context() as m:
        m.setattr(flow, "RevisionHistorySaver", Interrupted)
        with pytest.raises(RuntimeError):
            generate_document(APP, "SRS", None)
    key = f"{APP}.Outputs.SRS"
    assert [r["version"] for r in json.loads(document_store.stored_row(f"{key}.RevisionHistory")["Value"])["revisions"]] == ["0.1"]
    assert document_store.stored_row(key)["Version"] == 2  # the body is ahead of its history

    report = generate_document(APP, "SRS", None)  # the body is UNCHANGED, yet the history catches up

    assert report.body_action.value == "UNCHANGED" and report.revision_added.startswith("Revision recorded late")
    revisions = json.loads(document_store.stored_row(f"{key}.RevisionHistory")["Value"])["revisions"]
    assert [r["version"] for r in revisions] == ["0.1", "0.2"] and revisions[1]["date"] == "2026-10-09"
    control = document_store.stored_model(DocumentControl, f"{key}.DocumentControl")
    assert (control.document_version, control.last_updated_date) == ("0.2", "2026-10-09")
    again = generate_document(APP, "SRS", None)  # nothing is behind any more
    assert again.revision_added == "" and again.output_files == []
