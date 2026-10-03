"""Entity savers write the OKF columns, history and bundle file; Value-only hashing, in-place metadata refresh, trust defaults."""
import json
from pathlib import Path

import pytest

from docfactory import bundle, clock, db, facts
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.documentsaver.shared.document_control_saver import DocumentControlSaver
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_source import FactSource
from docfactory.models.save_action import SaveAction

yaml = pytest.importorskip("yaml")

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "json" / "application_overview"
KEY = "ReadmeForge.ApplicationOverview"
pytestmark = pytest.mark.usefixtures("tmp_db")


def _payload(name="readmeforge_minimal.json"):
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def _meta(**changes):
    return FactMeta(**{"generated_by": "okf-extraction-agent/m", "title": "ReadmeForge overview", "description": "What it is.",
                       "tags": ["overview"], "sources": [FactSource(resource="ReadmeForge/srs.pdf", id="srs")], **changes})


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch):
    times = iter(f"2026-10-0{day}T10:00:00Z" for day in range(1, 9))
    monkeypatch.setattr(clock, "now_iso", lambda: next(times))


def _file():
    return bundle.bundles_root() / "ReadmeForge" / "ApplicationOverview.md"


def _front(text):
    return yaml.safe_load(text.split("\n---\n", 1)[0].removeprefix("---\n"))


def test_created_fact_has_okf_columns_a_bundle_file_and_no_history():
    result = ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    assert result.action == SaveAction.CREATED and result.version == 1
    row = db.get_row("KnowledgeFacts", KEY)
    assert row["FilePath"] == "bundles/ReadmeForge/ApplicationOverview.md"
    assert (row["GeneratedBy"], row["GeneratedAt"]) == ("okf-extraction-agent/m", "2026-10-01T10:00:00Z")
    assert (row["Status"], row["Verified"], row["StaleAfter"]) == ("draft", "[]", None)
    text = _file().read_text(encoding="utf-8")
    assert text == "---\n" + row["YmlFrontmatter"] + "---\n\n" + text.split("---\n\n", 1)[1]
    data = _front(text)
    assert data["type"] == "Application Overview" and data["title"] == "ReadmeForge overview"
    assert data["fact_key"] == KEY and data["status"] == "draft" and "verified" not in data
    assert data["sources"][0]["resource"] == "ReadmeForge/srs.pdf"
    assert "# ReadmeForge overview" in text and "## Application name" in text
    assert db.list_fact_history(KEY) == []
    assert db.list_fact_keys_by_source("ReadmeForge/srs.pdf") == [KEY]


def test_same_value_and_same_metadata_is_unchanged_and_rewrites_nothing():
    ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    before, stamp = db.get_row("KnowledgeFacts", KEY), _file().stat().st_mtime_ns
    result = ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    assert result.action == SaveAction.UNCHANGED and db.get_row("KnowledgeFacts", KEY) == before
    assert _file().stat().st_mtime_ns == stamp


def test_same_value_without_metadata_leaves_the_row_and_file_alone():
    ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    before = db.get_row("KnowledgeFacts", KEY)
    assert ApplicationOverviewSaver().save(KEY, _payload()).action == SaveAction.UNCHANGED
    assert db.get_row("KnowledgeFacts", KEY) == before


def test_new_source_and_tags_refresh_the_metadata_in_place_without_a_version_bump():
    ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    before = db.get_row("KnowledgeFacts", KEY)
    newer = _meta(generated_by="someone/else", tags=["overview", "sre"], stale_after="2027-01-01T00:00:00Z",
                  sources=[FactSource(resource="ReadmeForge/srs.pdf"), FactSource(resource="ReadmeForge/arch.docx")])
    result = ApplicationOverviewSaver().save(KEY, _payload(), meta=newer)
    row = db.get_row("KnowledgeFacts", KEY)
    assert result.action == SaveAction.UNCHANGED and result.version == 1
    assert (row["Value"], row["Hashcode"], row["Version"], row["Completeness"]) == (
        before["Value"], before["Hashcode"], 1, before["Completeness"])
    assert (row["GeneratedBy"], row["GeneratedAt"]) == (before["GeneratedBy"], before["GeneratedAt"])  # the content was not regenerated
    assert row["StaleAfter"] == "2027-01-01T00:00:00Z" and row["YmlFrontmatter"] != before["YmlFrontmatter"]
    data = _front(_file().read_text(encoding="utf-8"))
    assert data["tags"] == ["overview", "sre"] and len(data["sources"]) == 2 and data["version"] == 1
    assert db.list_fact_keys_by_source("ReadmeForge/arch.docx") == [KEY]
    assert db.list_fact_history(KEY) == []


def test_changed_value_bumps_the_version_regenerates_and_adds_a_history_row():
    ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    result = ApplicationOverviewSaver().save(KEY, _payload("readmeforge_partial.json"), meta=_meta(generated_by="agent/2"))
    row = db.get_row("KnowledgeFacts", KEY)
    assert result.action == SaveAction.UPDATED and result.version == 2
    assert (row["GeneratedBy"], row["GeneratedAt"], row["Status"], row["Verified"]) == ("agent/2", "2026-10-02T10:00:00Z", "draft", "[]")
    assert db.list_fact_history(KEY) == [{"FactKey": KEY, "Hashcode": result.hashcode, "Version": 2,
                                          "Timestamp": "2026-10-02T10:00:00Z", "GeneratedBy": "agent/2"}]
    assert _front(_file().read_text(encoding="utf-8"))["version"] == 2


def test_same_json_in_gives_the_same_file_out():
    ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    first = _file().read_bytes()
    _file().unlink()
    db.connect().close()
    from docfactory import bundle_rebuild
    assert bundle_rebuild.rebuild()[:2] == (1, 0) and _file().read_bytes() == first


def test_without_metadata_a_fact_gets_the_bare_defaults():
    ApplicationOverviewSaver().save(KEY, _payload())
    row = db.get_row("KnowledgeFacts", KEY)
    assert row["GeneratedBy"] == "docfactory/unspecified" and _front(_file().read_text(encoding="utf-8"))["title"] == KEY


def test_a_row_saved_before_phase_3_gets_its_okf_data_when_saved_again_with_metadata():
    result = ApplicationOverviewSaver().save(KEY, _payload())
    db.write_row("KnowledgeFacts", KEY, db.get_row("KnowledgeFacts", KEY)["Value"], result.hashcode, "ReadmeForge", result.completeness, 1)
    _file().unlink()
    assert db.get_row("KnowledgeFacts", KEY)["YmlFrontmatter"] is None
    assert ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta()).action == SaveAction.UNCHANGED
    row = db.get_row("KnowledgeFacts", KEY)
    assert row["YmlFrontmatter"] and row["GeneratedBy"] == "okf-extraction-agent/m" and _file().is_file()


def test_unsafe_component_key_is_rejected_and_nothing_is_written(tmp_path):
    from docfactory.entitysaver.architecture_saver import ArchitectureSaver
    result = ArchitectureSaver().save("ReadmeForge.Components.a/b.Architecture", {})
    assert not result.ok and result.errors[0].error_type == "key_unsafe_path"
    assert db.list_rows("KnowledgeFacts") == [] and not bundle.bundles_root().exists()


def test_a_rejected_payload_writes_no_file():
    result = ApplicationOverviewSaver().save(KEY, {"nonsense": 1}, meta=_meta())
    assert not result.ok and not _file().exists() and db.list_rows("KnowledgeFacts") == []


def test_documents_take_no_metadata_and_write_no_bundle_file():
    result = DocumentControlSaver().save("ReadmeForge.Outputs.SMTD.DocumentControl", {}, meta=_meta())
    assert not result.ok and result.errors[0].error_type == "meta_not_allowed"
    assert not bundle.bundles_root().exists()


def test_typed_reads_return_fact_records():
    ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    record = facts.get_fact(KEY)
    assert record.key == KEY and record.version == 1 and record.status.value == "draft" and record.verified == []
    assert record.generated_by == "okf-extraction-agent/m" and record.file_path == "bundles/ReadmeForge/ApplicationOverview.md"
    assert facts.get_fact("Nope.Missing") is None
    assert [f.key for f in facts.list_facts("ReadmeForge")] == [KEY] and facts.list_facts("Other") == []
    assert [f.key for f in facts.list_facts_by_source("ReadmeForge/srs.pdf")] == [KEY]
    assert facts.list_facts_by_source("unknown.pdf") == []
