"""Release and revision history is never tagged: release features are not requirements."""
import pytest

from docfactory.bundle.paths import bundle_root
from docfactory.bundle.source_store import SourceStore
from docfactory.ingest import chunk_rebuild, pipeline
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.ingest.paths import INCOMING_ENV, STAGING_ENV
from docfactory.ingest.tagging import is_history, tag_chunk
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.doc_chunk import DocChunk
from docfactory.ontology.signals import load_signals

CLOCK = lambda: "2026-10-11T12:00:00+00:00"  # noqa: E731


def chunk(heading, text="FR-01. The system SHALL export shortlists."):
    return DocChunk(chunk_no=1, heading=heading, text=text, text_hash="0" * 64)


@pytest.mark.parametrize("heading", ["Release Notes", "Release Notes > Release 1.3.2 > Additions", "3. Change Log", "Changelog", "Version History", "2. Revision History", "What's new in 1.4"])
def test_history_headings_are_recognised(heading):
    assert is_history(chunk(heading))


@pytest.mark.parametrize("heading", ["3. Functional Requirements", "Release Management", "Release process", "Notes on releases"])
def test_other_headings_are_not_history(heading):
    assert not is_history(chunk(heading))


def test_a_history_chunk_gets_no_rule_tag_even_with_a_strong_signal():
    signals = load_signals()
    assert tag_chunk(chunk("3. Functional Requirements"), signals)  # the same text elsewhere is tagged
    assert tag_chunk(chunk("Release Notes > Release 1.3.2 > Additions"), signals) == []


class Greedy:
    """A fallback that tags every chunk it is shown as FunctionalRequirements, and remembers which ones it was shown."""
    origin = "llm/test"

    def __init__(self):
        self.asked = []

    def tag_chunks(self, chunks):
        self.asked += [c.chunk_no for c in chunks]
        return [ChunkTag(chunk_no=c.chunk_no, entity="FunctionalRequirements", origin="llm/test", score=0, evidence="test") for c in chunks], ""

    def decide_scope(self, chunks, tags, existing, reason):
        return None, "no"


@pytest.fixture
def dirs(tmp_bundle, tmp_path, monkeypatch):
    for name, env in (("incoming", INCOMING_ENV), ("staging", STAGING_ENV)):
        (tmp_path / name).mkdir()
        monkeypatch.setenv(env, str(tmp_path / name))
    return tmp_path


NOTES = """# Acme Product Pack

| Field | Value |
|---|---|
| Title | Acme |

## Release Notes
### Release 1.2
Some words that no entity claims here.

## Plans
Words about plans that no entity claims either.
"""


def test_the_llm_fallback_is_never_shown_history_chunks(dirs):
    (dirs / "staging" / "notes.md").write_text(NOTES, encoding="utf-8")
    fallback = Greedy()
    report = pipeline.ingest_staged("notes.md", CLOCK, fallback)
    record = SourceStore().read(report.target_path)
    shown = {c.chunk_no: c.heading for c in record.chunks}
    assert fallback.asked and all("Release" not in shown[no] for no in fallback.asked)
    tagged = {t.chunk_no for t in record.tags}
    assert all("Release" not in shown[no] for no in tagged)
    assert any("Release" in shown[no] and no in report.unmapped_chunks for no in shown)  # the history chunks stay unmapped (kept as notes later)


def test_chunk_rebuild_can_rebuild_just_the_named_originals(tmp_bundle):
    for name in ("a.md", "b.md"):
        original = bundle_root() / "Acme" / "references" / name
        original.parent.mkdir(parents=True, exist_ok=True)
        original.write_text("## Release Notes\nFR-01. The system SHALL do it.\n", encoding="utf-8")
        wrong = [ChunkTag(chunk_no=1, entity="FunctionalRequirements", origin="llm/x", score=0, evidence="x")]
        SourceStore().write(f"Acme/references/{name}", file_sha256(original), "2026-10-01T00:00:00Z", chunk_file(original), wrong)
    assert list(chunk_rebuild.rebuild_chunks(["Acme/references/a.md"])) == ["Acme/references/a.md"]
    assert SourceStore().read("Acme/references/a.md").tags == []  # rebuilt: the history chunk is no longer tagged
    assert len(SourceStore().read("Acme/references/b.md").tags) == 1  # left alone
    assert set(chunk_rebuild.rebuild_chunks()) == {"Acme/references/a.md", "Acme/references/b.md"}
