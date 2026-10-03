"""Opt-in live run of the ingestion pipeline with the real LLM fallback on the messy corpus: `pytest -m live tests/test_live_ingestion.py`.

The rules place most files; the fallback must tag what they leave (the informal ReadmeForge SRS, the standards PDF) and refuse a
scope for personal notes. Uses default_client() (settings from .env). Skipped when the server is not reachable.
"""
import shutil
from pathlib import Path

import pytest

from docfactory import db
from docfactory.agents.ingestion_fallback import IngestionFallback
from docfactory.agents.model_client_factory import default_client
from docfactory.ingest import pipeline
from docfactory.ingest.paths import DOCSTORE_ENV, INCOMING_ENV, STAGING_ENV
from docfactory.models.ingest_outcome import IngestOutcome
from tests.live_support import llm_available

CORPUS = Path(__file__).parent / "corpus"

pytestmark = [pytest.mark.live, pytest.mark.skipif(not llm_available(), reason="LLM server not reachable")]


def test_the_corpus_is_ingested_with_the_fallback(tmp_db, tmp_path, monkeypatch):
    incoming = tmp_path / "incoming"
    shutil.copytree(CORPUS / "incoming", incoming)
    monkeypatch.setenv(INCOMING_ENV, str(incoming))
    monkeypatch.setenv(STAGING_ENV, str(tmp_path / "staging"))
    monkeypatch.setenv(DOCSTORE_ENV, str(tmp_path / "DocStore"))
    fallback = IngestionFallback(default_client())

    reports = {r.file_name: r for r in pipeline.run_ingest(fallback=fallback)}
    print(pipeline.format_reports(list(reports.values())))

    stored = {name: r.target_path for name, r in reports.items() if r.outcome == IngestOutcome.NEW}
    assert stored["ReadmeForge SRS v0.3.pdf"] == "ReadmeForge/ReadmeForge SRS v0.3.pdf"
    assert stored["ReadmeForge_SystemMgmt.docx"].startswith("ReadmeForge/")
    assert stored["readmeforge-runbooks.html"].startswith("ReadmeForge/")
    assert stored["Platform Reliability Standards 2026.pdf"].startswith("shared/")
    assert reports["notes.txt"].outcome == IngestOutcome.STAGED
    assert reports["RF-requirements-copy.pdf"].outcome == IngestOutcome.STAGED  # same bytes as the SRS under another name

    srs_tags = db.list_doc_chunk_tags("ReadmeForge/ReadmeForge SRS v0.3.pdf")
    assert {"FunctionalRequirements", "NonFunctionalRequirements"} <= {t["Entity"] for t in srs_tags}, srs_tags
    assert all(t["Origin"].startswith("llm/") for t in srs_tags)  # its informal headings carry no rule signal

    shutil.copyfile(CORPUS / "revisions" / "ReadmeForge SRS v0.3.pdf", incoming / "ReadmeForge SRS v0.3.pdf")
    revised = {r.file_name: r for r in pipeline.run_ingest(fallback=fallback)}["ReadmeForge SRS v0.3.pdf"]
    print(pipeline.format_reports([revised]))
    assert (revised.outcome, revised.version) == (IngestOutcome.CHANGED, 2)
    assert "FunctionalRequirements" in revised.changed_entities
