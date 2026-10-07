"""The frontmatter vector index (FakeEmbedder, no server): rebuild, query, filtering, ranking and flags."""
import json
from contextlib import closing
from pathlib import Path

import pytest

from docfactory import clock, db
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.kpis_saver import KpisSaver
from docfactory.models.fact_meta import FactMeta
from docfactory.retrieval.fake_embedder import FakeEmbedder
from docfactory.retrieval.sqlite_vector_index import SqliteVectorIndex

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "json"
pytestmark = pytest.mark.usefixtures("tmp_db")


def _payload(folder, name):
    return json.loads((SAMPLES / folder / name).read_text(encoding="utf-8"))


def _save_overview(key, title, description, **meta):
    result = ApplicationOverviewSaver().save(
        key, _payload("application_overview", "readmeforge_minimal.json"),
        meta=FactMeta(generated_by="t/1", title=title, description=description, **meta))
    assert result.ok, result.errors


def _set_status(key, status):
    with closing(db.connect()) as con, con:
        con.execute("UPDATE KnowledgeFacts SET Status = ? WHERE FactKey = ?", (status, key))


@pytest.fixture
def index():
    _save_overview("ReadmeForge.ApplicationOverview", "ReadmeForge overview", "purpose and business owner of the readme generator")
    _save_overview("Other.ApplicationOverview", "Other overview", "payroll batch processing")
    result = KpisSaver().save("Shared.Kpis", _payload("kpis", "shared_devex_kpis_minimal.json"),
                              meta=FactMeta(generated_by="t/1", title="Shared KPIs", description="developer experience kpis"))
    assert result.ok, result.errors
    idx = SqliteVectorIndex(FakeEmbedder())
    idx.rebuild()
    return idx


def test_rebuild_embeds_every_fact_once_and_is_idempotent(index):
    assert len(db.list_index_rows()) == 3
    assert index.rebuild() == (0, 0)


def test_rebuild_embeds_only_changed_frontmatter_and_removes_deleted_facts(index):
    _save_overview("Other.ApplicationOverview", "Other overview", "now about invoicing")
    assert index.rebuild() == (1, 0)
    with closing(db.connect()) as con, con:
        con.execute("DELETE FROM KnowledgeFacts WHERE FactKey = 'Shared.Kpis'")
    assert index.rebuild() == (0, 1)
    assert [row["FactKey"] for row in db.list_index_rows()] == ["Other.ApplicationOverview", "ReadmeForge.ApplicationOverview"]


def test_a_new_embedding_model_re_embeds_everything(index):
    other = FakeEmbedder()
    other.model = "other-model"
    assert SqliteVectorIndex(other).rebuild() == (3, 0)


def test_query_ranks_the_closest_fact_first(index):
    hits = index.query("payroll batch processing")
    assert hits[0].key == "Other.ApplicationOverview"
    assert hits[0].title == "Other overview" and hits[0].type == "Application Overview"
    assert hits[0].description == "payroll batch processing"


def test_query_by_app_keeps_that_app_and_shared_facts(index):
    keys = {hit.key for hit in index.query("overview", app_id="ReadmeForge")}
    assert keys == {"ReadmeForge.ApplicationOverview", "Shared.Kpis"}


def test_stable_outranks_an_equally_close_draft(index):
    _save_overview("ReadmeForge.Components.api.ApplicationOverview", "ReadmeForge overview", "purpose and business owner of the readme generator")
    index.rebuild()
    _set_status("ReadmeForge.Components.api.ApplicationOverview", "stable")
    hits = index.query("ReadmeForge overview purpose and business owner of the readme generator", app_id="ReadmeForge")
    assert [h.key for h in hits[:2]] == ["ReadmeForge.Components.api.ApplicationOverview", "ReadmeForge.ApplicationOverview"]
    assert hits[0].status == "stable" and hits[1].status == "draft"


def test_deprecated_is_excluded_unless_asked_for(index):
    _set_status("Other.ApplicationOverview", "deprecated")
    assert "Other.ApplicationOverview" not in {h.key for h in index.query("payroll")}
    assert "Other.ApplicationOverview" in {h.key for h in index.query("payroll", include_deprecated=True)}


def test_stale_facts_are_flagged(index, monkeypatch):
    _save_overview("Other.ApplicationOverview", "Other overview", "payroll batch processing", stale_after="2026-11-01T00:00:00Z")
    index.rebuild()
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-03T10:00:00Z")
    assert not {h.key: h.stale for h in index.query("payroll")}["Other.ApplicationOverview"]
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-11-01T00:00:00Z")
    assert {h.key: h.stale for h in index.query("payroll")}["Other.ApplicationOverview"]


def test_query_on_an_empty_index_returns_nothing():
    assert SqliteVectorIndex(FakeEmbedder()).query("anything") == []


def test_query_limit(index):
    assert len(index.query("overview", limit=2)) == 2
