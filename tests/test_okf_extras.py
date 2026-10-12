"""OKF extras (redesign step 7): source labels and per-claim footnotes, the author of an original, per-scope indexes."""
import pytest

from docfactory import clock
from docfactory.bundle.bundle_store import BundleStore
from docfactory.bundle.paths import bundle_root
from docfactory.bundle.source_store import SourceStore
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.ingest.file_properties import file_author
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_source import FactSource
from docfactory.okf_frontmatter import source_labels

KEY = "Acme.FunctionalRequirements"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "now_iso", lambda: "2026-10-11T10:00:00Z")


def test_source_labels_come_from_the_file_name_and_stay_unique():
    sources = [FactSource(resource="Acme/references/Annex A SRS.pdf"), FactSource(resource="Acme/references/Annex A SRS.docx"),
               FactSource(resource="https://example.com/"), FactSource(resource="x/y", id="given")]
    assert source_labels(sources) == ["annex-a-srs", "annex-a-srs-2", "source", "given"]


def test_items_cite_their_sources_by_footnote_and_the_frontmatter_carries_the_label_and_author(tmp_bundle):
    sources = [FactSource(resource="Acme/references/srs.pdf", title="srs.pdf", author="Product Office", last_modified="2026-10-01T00:00:00Z")]
    BundleStore().write_fact(KEY, {"requirements": [{"id": "FR-01", "title": "T", "description": "The system SHALL log in."}]}, FactMeta(generated_by="t/1", sources=sources))
    item = (bundle_root() / "Acme/FunctionalRequirements/requirements/FR-01.md").read_text(encoding="utf-8")
    assert '    id: "srs"' in item and '    author: "Product Office"' in item
    assert "# Provenance" in item and "extracted from.[^srs]" in item and "[^srs]: srs.pdf, Product Office" in item
    parent = BundleStore().read_fact(KEY)
    assert parent.sources[0].id == "srs" and parent.sources[0].author == "Product Office"


def test_an_item_of_a_fact_without_sources_has_no_provenance_section(tmp_bundle):
    BundleStore().write_fact(KEY, {"requirements": [{"id": "FR-01", "title": "T", "description": "The system SHALL log in."}]})
    assert "# Provenance" not in (bundle_root() / "Acme/FunctionalRequirements/requirements/FR-01.md").read_text(encoding="utf-8")


def test_the_author_of_an_original_is_kept_in_its_source_and_survives_a_retag(tmp_bundle):
    original = bundle_root() / "Acme/references/page.html"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text('<html><head><meta name="author" content="  Jane   Doe "></head><body><h1>Intro</h1><p>Text.</p></body></html>', encoding="utf-8")
    assert file_author(original) == "Jane Doe"
    store = SourceStore()
    chunks = chunk_file(original)
    store.write("Acme/references/page.html", file_sha256(original), "2026-10-01T00:00:00Z", chunks, [], file_author(original))
    assert store.read("Acme/references/page.html").author == "Jane Doe"
    assert 'author: "Jane Doe"' in (bundle_root() / "Acme/sources/page.html.md").read_text(encoding="utf-8")
    store.write("Acme/references/page.html", file_sha256(original), "2026-10-01T00:00:00Z", chunks, [])  # a re-tag passes no author
    assert store.read("Acme/references/page.html").author == "Jane Doe"
    store.write("Acme/references/page.html", "0" * 64, "2026-10-02T00:00:00Z", chunks, [])  # another revision without an author names none
    assert store.read("Acme/references/page.html").author is None


def test_files_without_properties_or_unreadable_ones_name_no_author(tmp_path):
    text = tmp_path / "a.txt"
    text.write_text("plain", encoding="utf-8")
    broken = tmp_path / "b.pdf"
    broken.write_bytes(b"not a pdf")
    docx = tmp_path / "c.docx"
    docx.write_bytes(b"not a zip")
    assert (file_author(text), file_author(broken), file_author(docx), file_author(tmp_path / "missing.html")) == (None, None, None, None)


def test_word_documents_name_their_author(tmp_path):
    import docx
    document = docx.Document()
    document.core_properties.author = "Rita Writer"
    document.add_paragraph("Hello.")
    path = tmp_path / "d.docx"
    document.save(str(path))
    assert file_author(path) == "Rita Writer"


def test_every_scope_has_an_index_of_its_facts_graph_and_sources(tmp_bundle):
    from docfactory.agents.run_graph import write_graphs
    BundleStore().write_fact(KEY, {"requirements": [{"id": "FR-01", "title": "T", "description": "The system SHALL log in."}]}, FactMeta(generated_by="t/1", title="Acme requirements", description="What Acme does."))
    (bundle_root() / "Acme/sources").mkdir(parents=True, exist_ok=True)
    (bundle_root() / "Acme/sources/srs v1.pdf.md").write_text("---\ntype: Source\n---\n", encoding="utf-8")
    write_graphs(["Acme"])
    BundleStore().write_fact("Shared.Kpis", {"kpis": [{"name": "Uptime", "definition": "Share of time the service answers."}]})  # refreshes the indexes
    index = (bundle_root() / "Acme/index.md").read_text(encoding="utf-8")
    assert index.startswith("# Acme\n") and not index.startswith("---")
    assert "* [Acme requirements](/Acme/FunctionalRequirements.md) - What Acme does. ([items](/Acme/FunctionalRequirements/))" in index
    assert "(/Acme/graph/relationships.md)" in index and "(/Acme/sources/srs%20v1.pdf.md)" in index
    assert (bundle_root() / "Shared/index.md").is_file() and "Relationships" not in (bundle_root() / "Shared/index.md").read_text(encoding="utf-8")
    assert 'okf_version: "0.2"' in (bundle_root() / "index.md").read_text(encoding="utf-8")
    assert [f.key for f in BundleStore().list_facts()] == [KEY, "Shared.Kpis"]  # the indexes are not facts
