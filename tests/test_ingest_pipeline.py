"""The deterministic ingestion pipeline (Phase 2 redesign, step 4): stage, lookup, chunk, tag, scope, move and commit."""
import shutil
from pathlib import Path

import pytest

from docfactory.agents import run_ingestion
from docfactory.bundle.paths import bundle_root
from docfactory.bundle.source_store import SourceStore
from docfactory.canonical import sha256_hex
from docfactory.ingest import chunk_rebuild, pipeline
from docfactory.ingest.paths import INCOMING_ENV, STAGING_ENV
from docfactory.models.ingest_outcome import IngestOutcome

CORPUS = Path(__file__).parent / "corpus" / "incoming"
CLOCK = lambda: "2026-10-03T12:00:00+00:00"  # noqa: E731

SRS_V1 = """# Acme Software Requirements Specification

## 1. Introduction
Acme lets people book rooms.

## 3. Functional Requirements
| ID | Requirement |
|---|---|
| FR-01 | The system SHALL let users book a room. |

## 5. Non-Functional Requirements
| ID | Requirement |
|---|---|
| NFR-01 | Pages load within 2 seconds. |
"""


@pytest.fixture
def dirs(tmp_bundle, tmp_path, monkeypatch):
    paths = {name: tmp_path / name for name in ("incoming", "staging")}
    for path in paths.values():
        path.mkdir()
    monkeypatch.setenv(INCOMING_ENV, str(paths["incoming"]))
    monkeypatch.setenv(STAGING_ENV, str(paths["staging"]))
    paths["bundle"] = bundle_root()  # tmp_bundle selects a temporary bundle
    return paths


def drop(dirs, name, text=None, source=None):
    target = dirs["incoming"] / name
    if source is not None:
        shutil.copyfile(source, target)
    else:
        target.write_text(text, encoding="utf-8")
    return target


def only(reports):
    assert len(reports) == 1, reports
    return reports[0]


def test_a_new_file_is_staged_chunked_tagged_scoped_and_stored(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    report = only(pipeline.run_ingest(CLOCK))
    assert (report.outcome, report.target_path, report.version) == (IngestOutcome.NEW, "Acme/references/acme-srs.md", 1)
    assert (dirs["bundle"] / "Acme" / "references" / "acme-srs.md").is_file()
    assert (dirs["bundle"] / "Acme" / "sources" / "acme-srs.md.md").is_file()
    assert not any(dirs["incoming"].iterdir()) and not any(dirs["staging"].iterdir())
    record = SourceStore().read("Acme/references/acme-srs.md")
    assert record.version == 1
    assert [c.heading for c in record.chunks] == ["Acme Software Requirements Specification > 1. Introduction",
                                              "Acme Software Requirements Specification > 3. Functional Requirements",
                                              "Acme Software Requirements Specification > 5. Non-Functional Requirements"]
    tags = {(t.chunk_no, t.entity) for t in record.tags}
    assert tags == {(1, "ApplicationOverview"), (2, "FunctionalRequirements"), (3, "NonFunctionalRequirements")}
    assert report.entity_summary == ["ApplicationOverview: 1 chunks", "FunctionalRequirements: 1 chunks", "NonFunctionalRequirements: 1 chunks"]
    assert "Acme" in report.reason


def test_the_same_file_again_is_same_and_the_copy_is_discarded(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    drop(dirs, "acme-srs.md", SRS_V1)
    report = only(pipeline.run_ingest(CLOCK))
    assert (report.outcome, report.version, report.chunk_count) == (IngestOutcome.SAME, 1, 3)
    assert not any(dirs["staging"].iterdir())
    assert SourceStore().read("Acme/references/acme-srs.md").version == 1


def test_a_stored_source_whose_original_is_gone_is_repaired_not_discarded(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    (dirs["bundle"] / "Acme" / "references" / "acme-srs.md").unlink()  # the data-loss case: a Source without its original
    drop(dirs, "acme-srs.md", SRS_V1)
    report = only(pipeline.run_ingest(CLOCK))
    assert (report.outcome, report.version) == (IngestOutcome.REPAIRED, 1)
    assert (dirs["bundle"] / "Acme" / "references" / "acme-srs.md").read_text(encoding="utf-8") == SRS_V1


def test_a_new_revision_is_changed_in_its_scope_and_names_the_entities_to_re_extract(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    drop(dirs, "acme-srs.md", SRS_V1.replace("book a room.", "book and cancel a room."))
    report = only(pipeline.run_ingest(CLOCK))
    assert (report.outcome, report.target_path, report.version) == (IngestOutcome.CHANGED, "Acme/references/acme-srs.md", 2)
    assert report.changed_entities == ["FunctionalRequirements"]
    assert SourceStore().read("Acme/references/acme-srs.md").version == 2
    assert "cancel" in (dirs["bundle"] / "Acme" / "references" / "acme-srs.md").read_text(encoding="utf-8")
    assert "* **Update**: [Acme/references/acme-srs.md](/Acme/sources/acme-srs.md.md) v2 by docfactory/ingestion" in (dirs["bundle"] / "log.md").read_text(encoding="utf-8")


def test_same_content_under_another_name_stays_in_staging(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    drop(dirs, "copy of acme.md", SRS_V1)
    report = only(pipeline.run_ingest(CLOCK))
    assert report.outcome == IngestOutcome.STAGED and "Acme/references/acme-srs.md" in report.reason
    assert (dirs["staging"] / "copy of acme.md").is_file()


def test_a_name_stored_in_two_scopes_is_ambiguous(dirs):
    SourceStore().write("A/references/x.md", sha256_hex("one"), "t", [], [])
    SourceStore().write("B/references/x.md", sha256_hex("two"), "t", [], [])
    drop(dirs, "x.md", SRS_V1)
    report = only(pipeline.run_ingest(CLOCK))
    assert report.outcome == IngestOutcome.STAGED and "several scopes" in report.reason


def test_an_unsure_scope_and_an_empty_file_stay_in_staging_and_are_retried(dirs):
    drop(dirs, "notes.txt", source=CORPUS / "notes.txt")
    drop(dirs, "empty.txt", "")
    reports = {r.file_name: r for r in pipeline.run_ingest(CLOCK)}
    assert reports["notes.txt"].outcome == IngestOutcome.STAGED and reports["notes.txt"].reason.startswith("scope unsure")
    assert reports["notes.txt"].unmapped_chunks == [1]
    assert reports["empty.txt"].outcome == IngestOutcome.STAGED and "no extractable text" in reports["empty.txt"].reason
    assert {r.file_name for r in pipeline.run_ingest(CLOCK)} == {"notes.txt", "empty.txt"}  # still waiting, tried again
    assert SourceStore().list() == []


def test_an_unsupported_file_type_stays_in_staging(dirs):
    (dirs["incoming"] / "photo.png").write_bytes(b"\x89PNG")
    report = only(pipeline.run_ingest(CLOCK))
    assert report.outcome == IngestOutcome.STAGED and "no chunker" in report.reason


def test_an_existing_scope_folder_is_reused(dirs):
    drop(dirs, "ReadmeForge_SystemMgmt.docx", source=CORPUS / "ReadmeForge_SystemMgmt.docx")
    drop(dirs, "readmeforge-runbooks.html", source=CORPUS / "readmeforge-runbooks.html")
    reports = pipeline.run_ingest(CLOCK)
    assert {r.target_path for r in reports} == {"ReadmeForge/references/ReadmeForge_SystemMgmt.docx", "ReadmeForge/references/readmeforge-runbooks.html"}


def test_a_failed_source_write_puts_the_file_back_in_staging(dirs, monkeypatch):
    drop(dirs, "acme-srs.md", SRS_V1)

    def fail(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(SourceStore, "write", fail)
    with pytest.raises(RuntimeError):
        pipeline.run_ingest(CLOCK)
    assert (dirs["staging"] / "acme-srs.md").is_file()
    assert not (dirs["bundle"] / "Acme" / "references" / "acme-srs.md").exists()


def test_a_failed_write_of_a_revision_restores_the_stored_original(dirs, monkeypatch):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    drop(dirs, "acme-srs.md", SRS_V1 + "\nMore.\n")
    monkeypatch.setattr(SourceStore, "write", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("locked")))
    with pytest.raises(RuntimeError):
        pipeline.run_ingest(CLOCK)
    assert (dirs["bundle"] / "Acme" / "references" / "acme-srs.md").read_text(encoding="utf-8") == SRS_V1
    assert (dirs["staging"] / "acme-srs.md").read_text(encoding="utf-8").endswith("More.\n")


def test_chunk_rebuild_rewrites_the_outline_and_tags_and_reports_missing_files(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    SourceStore().write("Gone/references/lost.md", sha256_hex("lost"), "t", [], [])
    source_file = dirs["bundle"] / "Acme" / "sources" / "acme-srs.md.md"
    stripped = source_file.read_text(encoding="utf-8")
    source_file.write_text(stripped[:stripped.index("chunks:")] + "chunks: []\nchunk_tags: []\n---\n", encoding="utf-8")
    assert SourceStore().read("Acme/references/acme-srs.md").tags == []
    outcomes = chunk_rebuild.rebuild_chunks()
    assert outcomes == {"Acme/references/acme-srs.md": "3 chunks, 3 tags", "Gone/references/lost.md": "missing on disk"}
    record = SourceStore().read("Acme/references/acme-srs.md")
    assert len(record.tags) == 3 and len(record.chunks) == 3 and record.version == 1


def test_a_source_concept_is_an_okf_file_with_the_outline_and_tags_but_no_chunk_text(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    text = (dirs["bundle"] / "Acme" / "sources" / "acme-srs.md.md").read_text(encoding="utf-8")
    assert text.startswith('---\ntype: "Source"\ntitle: "acme-srs.md"\nresource: "Acme/references/acme-srs.md"\n')
    assert 'generated: { by: "docfactory/ingestion", at: "2026-10-03T12:00:00+00:00" }' in text
    assert "chunk_tags:" in text and '{ chunk: 2, entity: "FunctionalRequirements", origin: "rule"' in text
    assert "The system SHALL let users book a room" not in text


def test_shared_originals_go_to_the_folder_of_the_shared_facts(dirs):
    assert pipeline.existing_scopes() == []
    (dirs["bundle"] / "Shared").mkdir(parents=True)
    assert pipeline.existing_scopes() == ["Shared"]


def test_the_entry_point_prints_the_report(dirs, capsys, monkeypatch):
    monkeypatch.setattr(run_ingestion, "load_env_file", lambda: None)
    assert run_ingestion.main(["--no-llm"]) == 0
    assert "nothing to ingest" in capsys.readouterr().out
    drop(dirs, "acme-srs.md", SRS_V1)
    run_ingestion.main(["--no-llm"])
    out = capsys.readouterr().out
    assert "acme-srs.md: NEW -> Acme/references/acme-srs.md (v1)" in out and "FunctionalRequirements: 1 chunks" in out
