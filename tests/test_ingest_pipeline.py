"""The deterministic ingestion pipeline (Phase 2 redesign, step 4): stage, lookup, chunk, tag, scope, move and commit."""
import shutil
from pathlib import Path

import pytest

from docfactory import db
from docfactory.agents import run_ingestion
from docfactory.ingest import chunk_rebuild, pipeline
from docfactory.ingest.paths import DOCSTORE_ENV, INCOMING_ENV, STAGING_ENV
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
def dirs(tmp_db, tmp_path, monkeypatch):
    paths = {name: tmp_path / name for name in ("incoming", "staging", "DocStore")}
    for path in paths.values():
        path.mkdir()
    monkeypatch.setenv(INCOMING_ENV, str(paths["incoming"]))
    monkeypatch.setenv(STAGING_ENV, str(paths["staging"]))
    monkeypatch.setenv(DOCSTORE_ENV, str(paths["DocStore"]))
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
    assert (report.outcome, report.target_path, report.version) == (IngestOutcome.NEW, "Acme/acme-srs.md", 1)
    assert (dirs["DocStore"] / "Acme" / "acme-srs.md").is_file()
    assert not any(dirs["incoming"].iterdir()) and not any(dirs["staging"].iterdir())
    assert db.get_docstore_row("Acme/acme-srs.md")["Version"] == 1
    chunks = db.list_doc_chunks("Acme/acme-srs.md")
    assert [c["Heading"] for c in chunks] == ["Acme Software Requirements Specification > 1. Introduction",
                                              "Acme Software Requirements Specification > 3. Functional Requirements",
                                              "Acme Software Requirements Specification > 5. Non-Functional Requirements"]
    tags = {(t["ChunkNo"], t["Entity"]) for t in db.list_doc_chunk_tags("Acme/acme-srs.md")}
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
    assert db.list_docstore_history("Acme/acme-srs.md") == []


def test_a_stored_row_whose_file_is_gone_is_repaired_not_discarded(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    (dirs["DocStore"] / "Acme" / "acme-srs.md").unlink()  # the data-loss case: a row without its file
    drop(dirs, "acme-srs.md", SRS_V1)
    report = only(pipeline.run_ingest(CLOCK))
    assert (report.outcome, report.version) == (IngestOutcome.REPAIRED, 1)
    assert (dirs["DocStore"] / "Acme" / "acme-srs.md").read_text(encoding="utf-8") == SRS_V1


def test_a_new_revision_is_changed_in_its_scope_and_names_the_entities_to_re_extract(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    drop(dirs, "acme-srs.md", SRS_V1.replace("book a room.", "book and cancel a room."))
    report = only(pipeline.run_ingest(CLOCK))
    assert (report.outcome, report.target_path, report.version) == (IngestOutcome.CHANGED, "Acme/acme-srs.md", 2)
    assert report.changed_entities == ["FunctionalRequirements"]
    assert [h["Version"] for h in db.list_docstore_history("Acme/acme-srs.md")] == [2]
    assert "cancel" in db.list_doc_chunks("Acme/acme-srs.md")[1]["Text"]


def test_same_content_under_another_name_stays_in_staging(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    drop(dirs, "copy of acme.md", SRS_V1)
    report = only(pipeline.run_ingest(CLOCK))
    assert report.outcome == IngestOutcome.STAGED and "Acme/acme-srs.md" in report.reason
    assert (dirs["staging"] / "copy of acme.md").is_file()


def test_a_name_stored_in_two_scopes_is_ambiguous(dirs):
    db.write_docstore_row("A/x.md", "h1", "t")
    db.write_docstore_row("B/x.md", "h2", "t")
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
    assert db.list_docstore_rows() == []


def test_an_unsupported_file_type_stays_in_staging(dirs):
    (dirs["incoming"] / "photo.png").write_bytes(b"\x89PNG")
    report = only(pipeline.run_ingest(CLOCK))
    assert report.outcome == IngestOutcome.STAGED and "no chunker" in report.reason


def test_an_existing_scope_folder_is_reused(dirs):
    drop(dirs, "ReadmeForge_SystemMgmt.docx", source=CORPUS / "ReadmeForge_SystemMgmt.docx")
    drop(dirs, "readmeforge-runbooks.html", source=CORPUS / "readmeforge-runbooks.html")
    reports = pipeline.run_ingest(CLOCK)
    assert {r.target_path for r in reports} == {"ReadmeForge/ReadmeForge_SystemMgmt.docx", "ReadmeForge/readmeforge-runbooks.html"}


def test_a_failed_database_write_puts_the_file_back_in_staging(dirs, monkeypatch):
    drop(dirs, "acme-srs.md", SRS_V1)

    def fail(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(db, "commit_ingested", fail)
    with pytest.raises(RuntimeError):
        pipeline.run_ingest(CLOCK)
    assert (dirs["staging"] / "acme-srs.md").is_file()
    assert not (dirs["DocStore"] / "Acme" / "acme-srs.md").exists()


def test_a_failed_write_of_a_revision_restores_the_stored_original(dirs, monkeypatch):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    drop(dirs, "acme-srs.md", SRS_V1 + "\nMore.\n")
    monkeypatch.setattr(db, "commit_ingested", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("locked")))
    with pytest.raises(RuntimeError):
        pipeline.run_ingest(CLOCK)
    assert (dirs["DocStore"] / "Acme" / "acme-srs.md").read_text(encoding="utf-8") == SRS_V1
    assert (dirs["staging"] / "acme-srs.md").read_text(encoding="utf-8").endswith("More.\n")


def test_chunk_rebuild_rewrites_chunks_and_reports_missing_files(dirs):
    drop(dirs, "acme-srs.md", SRS_V1)
    pipeline.run_ingest(CLOCK)
    db.write_docstore_row("Gone/lost.md", "h", "t")
    with db.connect() as con:
        con.execute("DELETE FROM DocChunkTags")
    outcomes = chunk_rebuild.rebuild_chunks()
    assert outcomes == {"Acme/acme-srs.md": "3 chunks, 3 tags", "Gone/lost.md": "missing on disk"}
    assert len(db.list_doc_chunk_tags("Acme/acme-srs.md")) == 3
    assert db.get_docstore_row("Acme/acme-srs.md")["Version"] == 1


def test_the_entry_point_prints_the_report(dirs, capsys, monkeypatch):
    monkeypatch.setattr(run_ingestion, "load_env_file", lambda: None)
    assert run_ingestion.main([]) == 0
    assert "nothing to ingest" in capsys.readouterr().out
    drop(dirs, "acme-srs.md", SRS_V1)
    run_ingestion.main([])
    out = capsys.readouterr().out
    assert "acme-srs.md: NEW -> Acme/acme-srs.md (v1)" in out and "FunctionalRequirements: 1 chunks" in out
