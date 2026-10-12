"""Coverage report: where the content of each chunk of an ingested original ended up (redesign step 2)."""
import pytest
from pydantic import ValidationError

from docfactory.agents.run_coverage import main
from docfactory.bundle.contribution_store import ContributionStore
from docfactory.bundle.paths import bundle_root
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.batching import chunks_hash
from docfactory.extract.coverage import all_coverage, file_coverage, format_coverage
from docfactory.ingest.chunking import chunk_file
from docfactory.ingest.file_hash import file_sha256
from docfactory.models.chunk_coverage import ChunkCoverage
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.coverage_report import CoverageReport
from docfactory.models.coverage_status import CoverageStatus

APP = "Acme/references/srs.md"
GENERAL = "general/references/guide.md"
TEXTS = ["Intro text.", "FR-01. The system SHALL log in.", "Quality targets.", "Monitoring text.", "Loose notes."]


def store(path, entities_by_chunk):
    """Put `path` into the bundle (one markdown section per text) and record its Source with the tags given per chunk number."""
    original = bundle_root() / path
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("".join(f"## Section {n}\n{t}\n\n" for n, t in enumerate(TEXTS, 1)), encoding="utf-8")
    chunks = chunk_file(original)
    assert len(chunks) == len(TEXTS)
    tags = [ChunkTag(chunk_no=no, entity=e, origin="rule", score=4, evidence="test") for no, entities in entities_by_chunk.items() for e in entities]
    SourceStore().write(path, file_sha256(original), "2026-10-01T00:00:00Z", chunks, tags)
    return chunks


def contribute(path, entity, chunks, complete=True):
    ContributionStore().save(f"Acme.{entity}", path, {}, chunks_hash(chunks) if complete else None, None, "test/1", "2026-10-01T00:00:00Z")


def by_no(report):
    return {c.chunk_no: c for c in report.chunks}


def test_every_status_is_told_apart(tmp_bundle):
    chunks = store(APP, {1: ["ApplicationOverview"], 2: ["FunctionalRequirements"], 3: ["Slo"], 4: ["Monitoring"]})
    contribute(APP, "ApplicationOverview", [chunks[0]])
    contribute(APP, "Monitoring", [chunks[3]], complete=False)
    rows = by_no(file_coverage(APP))
    assert [rows[n].status for n in range(1, 6)] == [CoverageStatus.EXTRACTED, CoverageStatus.NOT_EXTRACTED, CoverageStatus.SKIPPED_SCOPE,
                                                     CoverageStatus.NOT_EXTRACTED, CoverageStatus.UNMAPPED]
    assert "not extracted from this file yet" in rows[2].reason and "Shared.Slo" in rows[3].reason
    assert "a batch failed" in rows[4].reason and rows[5].entities == [] and rows[1].reason == ""


def test_changed_chunks_since_the_last_extraction_are_not_extracted(tmp_bundle):
    chunks = store(APP, {2: ["FunctionalRequirements"]})
    ContributionStore().save("Acme.FunctionalRequirements", APP, {}, "0" * 64, None, "test/1", "2026-10-01T00:00:00Z")
    assert chunks
    assert "chunks changed" in by_no(file_coverage(APP))[2].reason


def test_a_chunk_takes_the_best_status_of_its_entities(tmp_bundle):
    chunks = store(APP, {1: ["ApplicationOverview", "Slo"]})
    contribute(APP, "ApplicationOverview", [chunks[0]])
    row = by_no(file_coverage(APP))[1]
    assert row.status == CoverageStatus.EXTRACTED and row.entities == ["ApplicationOverview", "Slo"]


def test_files_in_general_give_no_facts(tmp_bundle):
    store(GENERAL, {1: ["ApplicationOverview"]})
    row = by_no(file_coverage(GENERAL))[1]
    assert row.status == CoverageStatus.SKIPPED_SCOPE and "general/" in row.reason


def test_the_report_accounts_for_every_chunk_and_character(tmp_bundle):
    chunks = store(APP, {1: ["ApplicationOverview"]})
    report = file_coverage(APP)
    assert [c.chunk_no for c in report.chunks] == [1, 2, 3, 4, 5]
    assert sum(c.chars for c in report.chunks) == sum(len(c.text) for c in chunks)


def test_all_coverage_lists_every_original_and_text_names_the_losses(tmp_bundle):
    store(APP, {1: ["ApplicationOverview"]})
    store(GENERAL, {})
    reports = all_coverage()
    assert [r.path for r in reports] == sorted([APP, GENERAL])
    text = format_coverage(reports)
    assert f"{APP}: 5 chunks" in text and "UNMAPPED chunk 5" in text and "NOT_EXTRACTED" in text
    assert format_coverage([]) == "no ingested originals in the bundle"


def test_unknown_file_is_an_error(tmp_bundle):
    with pytest.raises(FileNotFoundError):
        file_coverage("Acme/references/missing.md")


def test_entry_point_prints_and_rejects_unknown_paths(tmp_bundle, capsys):
    store(APP, {1: ["ApplicationOverview"]})
    assert main([]) == 0 and APP in capsys.readouterr().out
    assert main([APP]) == 0
    assert main(["Acme/references/missing.md"]) == 1 and APP in capsys.readouterr().out


def test_models_validate():
    assert CoverageStatus("UNMAPPED") is CoverageStatus.UNMAPPED and all(m.value == m.name for m in CoverageStatus)
    row = ChunkCoverage(chunk_no=1, heading="H", status=CoverageStatus.UNMAPPED)
    assert row.chars == 0 and row.entities == [] and row.reason == ""
    assert CoverageReport(path="a/b").chunks == []
    with pytest.raises(ValidationError):
        ChunkCoverage(chunk_no=0, heading="H", status=CoverageStatus.UNMAPPED)
    with pytest.raises(ValidationError):
        CoverageReport(path="a", extra="x")
