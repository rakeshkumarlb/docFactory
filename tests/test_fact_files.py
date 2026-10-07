"""The JSON file of each knowledge fact under knowledgefacts/: paths, the writer, the saver hook and the rebuild command."""
import json

import pytest

from docfactory import db, fact_files
from docfactory.entitysaver.architecture_saver import ArchitectureSaver
from docfactory.entitysaver.kpis_saver import KpisSaver
from docfactory.entitysaver.sop_saver import SopSaver
from docfactory.models.save_action import SaveAction

SOP = {"procedures": [{"name": "Test-Restart", "steps": ["Test step one"]}], "notes": "Test notes"}


@pytest.mark.parametrize("key,path", [
    ("ReadmeForge.ApplicationOverview", "ReadmeForge/ApplicationOverview.json"),
    ("Shared.Kpis", "Shared/Kpis.json"),
    ("ReadmeForge.Components.api server.Architecture", "ReadmeForge/Components/api server/Architecture.json"),
])
def test_file_path_follows_the_key(key, path):
    assert fact_files.file_path_of(key) == path


@pytest.mark.parametrize("key", [
    "ReadmeForge.Components.a/b.Architecture", "ReadmeForge.Components.a\\b.Architecture", "ReadmeForge..Architecture",
    "ReadmeForge.Components. api.Architecture", "ReadmeForge.Components.c:d.Architecture", "ReadmeForge.Components.con.Architecture",
    "ReadmeForge.Components.x?.Architecture", "ReadmeForge.Components.\x00.Architecture",
])
def test_unsafe_key_segments_are_refused(key):
    with pytest.raises(ValueError, match="cannot be used as a file name"):
        fact_files.file_path_of(key)


def test_default_root_is_knowledgefacts_under_the_project(monkeypatch):
    monkeypatch.delenv(fact_files.ENV_VAR, raising=False)
    assert fact_files.facts_root() == fact_files.PROJECT_ROOT / "knowledgefacts"


def test_a_saved_fact_is_written_as_indented_json_in_model_field_order(tmp_db):
    assert SopSaver().save("ReadmeForge.Sop", SOP).action == SaveAction.CREATED
    path = fact_files.facts_root() / "ReadmeForge" / "Sop.json"
    text = path.read_text(encoding="utf-8")
    assert json.loads(text) == SopSaver.model.model_validate(SOP).model_dump(mode="json")
    assert text.index('"procedures"') < text.index('"notes"') and text.startswith("{\n  ") and text.endswith("}\n")


def test_shared_and_component_facts_get_their_own_folders(tmp_db):
    KpisSaver().save("Shared.Kpis", {})
    ArchitectureSaver().save("ReadmeForge.Components.api.Architecture", {})
    files = sorted(p.relative_to(fact_files.facts_root()).as_posix() for p in fact_files.facts_root().rglob("*.json"))
    assert files == ["ReadmeForge/Components/api/Architecture.json", "Shared/Kpis.json"]


def test_an_update_rewrites_the_file_and_an_unchanged_save_restores_a_deleted_one(tmp_db):
    SopSaver().save("ReadmeForge.Sop", SOP)
    path = fact_files.facts_root() / "ReadmeForge" / "Sop.json"
    assert SopSaver().save("ReadmeForge.Sop", {**SOP, "notes": "Test notes two"}).action == SaveAction.UPDATED
    assert json.loads(path.read_text(encoding="utf-8"))["notes"] == "Test notes two"
    path.unlink()
    assert SopSaver().save("ReadmeForge.Sop", {**SOP, "notes": "Test notes two"}).action == SaveAction.UNCHANGED
    assert path.is_file()


def test_an_unchanged_file_is_not_rewritten(tmp_db):
    SopSaver().save("ReadmeForge.Sop", SOP)
    fact = SopSaver.model.model_validate(SOP)
    assert fact_files.write_file("ReadmeForge.Sop", fact) is False
    assert fact_files.write_file("ReadmeForge.Sop", fact.model_copy(update={"notes": "Test notes changed"})) is True


def test_an_unsafe_key_is_rejected_and_nothing_is_written(tmp_db):
    result = ArchitectureSaver().save("ReadmeForge.Components.a/b.Architecture", {})
    assert not result.ok and result.errors[0].error_type == "key_unsafe_path"
    assert db.list_rows("KnowledgeFacts") == [] and not fact_files.facts_root().exists()


def test_a_rejected_payload_and_a_document_write_no_file(tmp_db):
    from docfactory.documentsaver.shared.document_control_saver import DocumentControlSaver
    assert not SopSaver().save("ReadmeForge.Sop", {"bogus": 1}).ok
    DocumentControlSaver().save("ReadmeForge.Outputs.SMTD.DocumentControl", {})
    assert not fact_files.facts_root().exists()


def test_rebuild_rewrites_missing_files_and_removes_orphans(tmp_db):
    SopSaver().save("ReadmeForge.Sop", SOP)
    KpisSaver().save("Shared.Kpis", {})
    root = fact_files.facts_root()
    (root / "Shared" / "Kpis.json").unlink()
    (root / "Old").mkdir()
    (root / "Old" / "Gone.json").write_text("{}", encoding="utf-8")
    assert fact_files.rebuild() == (1, 1, 1)
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*.json")) == ["ReadmeForge/Sop.json", "Shared/Kpis.json"]
    assert fact_files.main() == 0


COMPLETE_SOP = {"procedures": [{"name": "Test-Restart", "purpose": "Test purpose", "trigger": "Test trigger", "frequency": "Test frequency",
                                "roles": ["Test role"], "prerequisites": ["Test prerequisite"], "steps": ["Test step one"],
                                "verification": "Test verification", "escalation": "Test escalation"}],
                "notes": "Test notes"}


def test_open_questions_go_next_to_the_json_and_the_file_goes_when_nothing_is_open(tmp_db):
    SopSaver().save("ReadmeForge.Sop", SOP)
    missing = fact_files.facts_root() / "ReadmeForge" / "Sop.missing.md"
    text = missing.read_text(encoding="utf-8")
    assert text.startswith("# Open questions: ReadmeForge.Sop\n")
    assert "`procedures[].purpose` (missing in 1 of 1 items): What is the purpose of this procedure?\n   Assumed until answered: empty text" in text
    assert fact_files.missing_path_of("Shared.Kpis") == "Shared/Kpis.missing.md"
    assert SopSaver().save("ReadmeForge.Sop", COMPLETE_SOP).completeness == 100
    assert not missing.exists() and (fact_files.facts_root() / "ReadmeForge" / "Sop.json").is_file()


def test_rebuild_restores_a_deleted_questions_file_and_removes_an_orphan_one(tmp_db):
    SopSaver().save("ReadmeForge.Sop", SOP)
    root = fact_files.facts_root()
    (root / "ReadmeForge" / "Sop.missing.md").unlink()
    (root / "ReadmeForge" / "Gone.missing.md").write_text("x", encoding="utf-8")
    assert fact_files.rebuild() == (1, 0, 1)
    assert (root / "ReadmeForge" / "Sop.missing.md").is_file() and not (root / "ReadmeForge" / "Gone.missing.md").exists()
