"""Entity savers write the OKF columns and history (no file); Value-only hashing, in-place metadata refresh, trust defaults."""
import json
from pathlib import Path

import pytest

from docfactory import clock, db, facts
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


def _front():
    return yaml.safe_load(db.get_row("KnowledgeFacts", KEY)["YmlFrontmatter"])


def test_created_fact_has_okf_columns_and_no_history():
    result = ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    assert result.action == SaveAction.CREATED and result.version == 1
    row = db.get_row("KnowledgeFacts", KEY)
    assert "FilePath" not in row
    assert (row["FactType"], row["Title"], row["Description"]) == ("Application Overview", "ReadmeForge overview", "What it is.")
    assert json.loads(row["Tags"]) == ["overview"] and json.loads(row["Sources"]) == [{"resource": "ReadmeForge/srs.pdf", "id": "srs"}]
    assert (row["GeneratedBy"], row["GeneratedAt"]) == ("okf-extraction-agent/m", "2026-10-01T10:00:00Z")
    assert (row["Status"], row["Verified"], row["StaleAfter"]) == ("draft", "[]", None)
    data = _front()
    assert data["type"] == "Application Overview" and data["title"] == "ReadmeForge overview"
    assert data["fact_key"] == KEY and data["status"] == "draft" and "verified" not in data
    assert data["sources"][0]["resource"] == "ReadmeForge/srs.pdf"
    assert db.list_fact_history(KEY) == []
    assert db.list_fact_keys_by_source("ReadmeForge/srs.pdf") == [KEY]


def test_same_value_and_same_metadata_is_unchanged_and_rewrites_nothing():
    ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    before = db.get_row("KnowledgeFacts", KEY)
    result = ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    assert result.action == SaveAction.UNCHANGED and db.get_row("KnowledgeFacts", KEY) == before


def test_same_value_without_metadata_leaves_the_row_alone():
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
    data = _front()
    assert data["tags"] == ["overview", "sre"] and len(data["sources"]) == 2 and data["version"] == 1
    assert json.loads(row["Tags"]) == ["overview", "sre"] and len(json.loads(row["Sources"])) == 2
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
    assert _front()["version"] == 2


def test_same_json_in_gives_the_same_value_and_hash_out():
    first = ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    reordered = dict(reversed(list(_payload().items())))
    assert ApplicationOverviewSaver().save(KEY, reordered, meta=_meta()).action == SaveAction.UNCHANGED
    assert db.get_row("KnowledgeFacts", KEY)["Hashcode"] == first.hashcode


def test_without_metadata_a_fact_gets_the_bare_defaults():
    ApplicationOverviewSaver().save(KEY, _payload())
    row = db.get_row("KnowledgeFacts", KEY)
    assert row["GeneratedBy"] == "docfactory/unspecified" and row["Title"] == KEY and _front()["title"] == KEY


def test_a_row_saved_before_phase_3_gets_its_okf_data_when_saved_again_with_metadata():
    result = ApplicationOverviewSaver().save(KEY, _payload())
    db.write_row("KnowledgeFacts", KEY, db.get_row("KnowledgeFacts", KEY)["Value"], result.hashcode, "ReadmeForge", result.completeness, 1)
    db.update_fact_metadata(KEY, {"YmlFrontmatter": None, "FactType": None, "Title": None, "GeneratedBy": None, "GeneratedAt": None}, [])
    assert db.get_row("KnowledgeFacts", KEY)["YmlFrontmatter"] is None
    assert ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta()).action == SaveAction.UNCHANGED
    row = db.get_row("KnowledgeFacts", KEY)
    assert row["YmlFrontmatter"] and row["GeneratedBy"] == "okf-extraction-agent/m" and row["Title"] == "ReadmeForge overview"


def test_a_component_key_with_a_free_text_name_is_accepted():
    from docfactory.entitysaver.architecture_saver import ArchitectureSaver
    assert ArchitectureSaver().save("ReadmeForge.Components.api server/v2.Architecture", {}).ok  # no file name to protect any more


def test_a_rejected_payload_writes_nothing():
    result = ApplicationOverviewSaver().save(KEY, {"nonsense": 1}, meta=_meta())
    assert not result.ok and db.list_rows("KnowledgeFacts") == []


def test_documents_take_no_metadata():
    result = DocumentControlSaver().save("ReadmeForge.Outputs.SMTD.DocumentControl", {}, meta=_meta())
    assert not result.ok and result.errors[0].error_type == "meta_not_allowed"


def test_typed_reads_return_fact_records():
    ApplicationOverviewSaver().save(KEY, _payload(), meta=_meta())
    record = facts.get_fact(KEY)
    assert record.key == KEY and record.version == 1 and record.status.value == "draft" and record.verified == []
    assert record.generated_by == "okf-extraction-agent/m" and record.title == "ReadmeForge overview"
    assert record.type == "Application Overview" and record.tags == ["overview"]
    assert record.sources == [FactSource(resource="ReadmeForge/srs.pdf", id="srs")]
    assert facts.get_fact("Nope.Missing") is None
    assert [f.key for f in facts.list_facts("ReadmeForge")] == [KEY] and facts.list_facts("Other") == []
    assert [f.key for f in facts.list_facts_by_source("ReadmeForge/srs.pdf")] == [KEY]
    assert facts.list_facts_by_source("unknown.pdf") == []
