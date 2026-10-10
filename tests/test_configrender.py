"""Configuration-based rendering: YAML templates, one generic builder and renderer, parity with the model-based Phase 4 output."""
import json
from pathlib import Path

import pytest

from docfactory import clock, db
from docfactory.build import FACT_SPECS
from docfactory.configrender import configured_store
from docfactory.configrender.configured_document import generate_configured
from docfactory.configrender.render_configured import render_configured_markdown
from docfactory.configrender.template_error import TemplateError
from docfactory.configrender.template_loader import list_doc_types, load_template
from docfactory.documentmodels.shared.document_need import DocumentNeed
from docfactory.generate_configured import main
from docfactory.generation.doc_types import DOC_TYPES
from docfactory.generation.generate_document import generate
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


def test_the_four_shipped_templates_load_and_match_the_document_types():
    assert list_doc_types() == sorted(DOC_TYPES)
    for doc_type, spec in DOC_TYPES.items():
        template = load_template(doc_type)
        assert template.name == spec["name"]


@pytest.mark.parametrize("seeded", [list(FULL), ["ApplicationOverview", "FunctionalRequirements"], []], ids=["all-facts", "two-facts", "no-facts"])
def test_output_is_byte_identical_to_the_model_based_option(env, seeded):
    _seed(*seeded)
    for doc_type in DOC_TYPES:
        assert generate(APP, doc_type, None).errors == []
        assert generate_configured(APP, doc_type, None).errors == []
    model_based, configured = _files(env, APP), _files(env, f"configured/{APP}")
    assert set(model_based) == set(configured) and model_based
    for name in model_based:
        assert configured[name] == model_based[name], name


def test_stored_rows_are_separate_from_the_model_based_ones(env):
    _seed("ApplicationOverview")
    generate_configured(APP, "SRS", None)
    assert db.get_row("ConfiguredDocuments", f"{APP}.Configured.SRS") is not None
    assert db.get_row("DocumentOutputs", f"{APP}.Outputs.SRS") is None
    keys = {row["DocumentKey"] for row in db.list_rows("ConfiguredDocuments")}
    assert keys == {f"{APP}.Configured.SRS{part}" for part in ("", ".DocumentControl", ".RevisionHistory", ".MissingInfo")}


def test_missing_fact_is_a_gap_and_completeness_counts_answered_fields(env):
    _seed("ApplicationOverview")
    report = generate_configured(APP, "SRS", None)
    assert report.gap_count > 0
    body = json.loads(db.get_row("ConfiguredDocuments", f"{APP}.Configured.SRS")["Value"])
    fields = [f for s in body["sections"] for f in s["fields"]]
    answered = sum(f["status"] == "answered" for f in fields)
    assert 0 < answered < len(fields)
    assert report.body_completeness == pytest.approx(100 * answered / len(fields))
    assert "_Not provided._" in (env / "configured" / APP / "SRS.md").read_text(encoding="utf-8")


def test_second_run_changes_nothing_and_makes_no_llm_call(env):
    _seed(*FULL)
    writer = CountingWriter()
    generate_configured(APP, "SMTD", writer)
    first_calls = writer.calls
    rows = {r["DocumentKey"]: (r["Hashcode"], r["Version"]) for r in db.list_rows("ConfiguredDocuments")}
    again = generate_configured(APP, "SMTD", writer)
    assert {r["DocumentKey"]: (r["Hashcode"], r["Version"]) for r in db.list_rows("ConfiguredDocuments")} == rows
    assert again.output_files == [] and writer.calls == first_calls


def test_changed_fact_adds_one_revision_naming_the_section(env):
    _seed("ApplicationOverview", "FunctionalRequirements")
    generate_configured(APP, "SRS", None)
    payload = json.loads((SAMPLES / "functional_requirements" / "readmeforge_full.json").read_text(encoding="utf-8"))
    payload["summary"] = "A changed summary."
    assert entity_saver_for("FunctionalRequirements")().save(f"{APP}.FunctionalRequirements", payload).ok
    report = generate_configured(APP, "SRS", None)
    assert report.revision_added.startswith("Changed sections: functional_requirements (from ")
    history = configured_store.stored_row(f"{APP}.Configured.SRS.RevisionHistory")
    assert len(json.loads(history["Value"])["revisions"]) == 2


def test_needs_writer_is_used_and_kept_for_unchanged_gaps(env):
    _seed("ApplicationOverview")
    writer = CountingWriter()
    assert generate_configured(APP, "SRS", writer).needs_origin == "llm"
    assert writer.calls == 1
    assert generate_configured(APP, "SRS", writer).needs_skipped and writer.calls == 1


def test_rendering_without_document_control_fails_clearly(env):
    _seed("ApplicationOverview")
    generate_configured(APP, "SRS", None)
    with db.connect() as con:
        con.execute("DELETE FROM ConfiguredDocuments WHERE DocumentKey LIKE '%.DocumentControl'")
    with pytest.raises(RenderError, match="DocumentControl"):
        render_configured_markdown(APP, "SRS")


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
    assert (env / "configured" / APP / "Overview.md").exists()
    assert main(["Nobody", "all", "--no-llm"]) == 1
    assert "has no knowledge facts" in capsys.readouterr().out
