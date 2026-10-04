"""Opt-in live run of extraction against the corpus SRS and its revision: `pytest -m live`.

DocStore is filled deterministically by the ingestion pipeline (no LLM); only the extraction calls (one per batch of an entity's
chunks) are live. Uses default_client() (Ollama Cloud, local Ollama, or DOCFACTORY_PROVIDER=anthropic). Skipped when the chosen
server is not reachable.
"""
import json
import shutil
from pathlib import Path

import pytest

from docfactory import bundle, db, facts, okf_check
from docfactory.agents.entity_extractor import EntityExtractor
from docfactory.agents.model_client_factory import default_client
from docfactory.extract.extraction_pipeline import extract_file, format_reports
from docfactory.ingest import docstore_reads as ops
from docfactory.models.extraction_outcome import ExtractionOutcome
from docfactory.ingest import pipeline
from docfactory.ingest.paths import DOCSTORE_ENV, INCOMING_ENV, STAGING_ENV
from tests.live_support import llm_available as _llm_available  # also loads .env

CORPUS = Path(__file__).parent / "corpus"
SRS = "ReadmeForge SRS v0.3.pdf"
PATH = f"ReadmeForge/{SRS}"
EXPECTED_KEYS = {"ReadmeForge.ApplicationOverview", "ReadmeForge.FunctionalRequirements", "ReadmeForge.NonFunctionalRequirements"}

pytestmark = [pytest.mark.live, pytest.mark.skipif(not _llm_available(), reason="LLM server not reachable")]


def _store(source: Path, incoming: Path):
    shutil.copyfile(source, incoming / SRS)
    [report] = pipeline.run_ingest()
    assert report.target_path == PATH, report
    return report


def test_extraction_of_the_srs_and_then_its_revision(tmp_db, tmp_path, monkeypatch):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    monkeypatch.setenv(INCOMING_ENV, str(incoming))
    monkeypatch.setenv(DOCSTORE_ENV, str(tmp_path / "DocStore"))
    monkeypatch.setenv(STAGING_ENV, str(tmp_path / "staging"))
    assert _store(CORPUS / "incoming" / SRS, incoming).outcome.value == "NEW"
    text = ops.read_docstore_text(PATH)

    extractor = EntityExtractor(default_client())
    reports = extract_file(PATH, extractor)
    print(format_reports(PATH, reports))

    stored = {fact.key: fact for fact in facts.list_facts()}
    assert stored, "extraction saved no fact"
    assert set(stored) <= EXPECTED_KEYS | {k for k in stored if k.startswith("ReadmeForge.")}, list(stored)  # only this application's facts
    assert {"ReadmeForge.FunctionalRequirements", "ReadmeForge.NonFunctionalRequirements"} <= set(stored), list(stored)
    for fact in stored.values():
        assert fact.status.value == "draft" and fact.verified == [] and fact.generated_by.startswith("okf-extraction-agent/"), fact.key
        assert f'resource: "{PATH}"' in fact.frontmatter, fact.key  # the source is the file the chunks came from
    assert okf_check.check_bundle(bundle.bundles_root()) == []

    functional = json.loads(stored["ReadmeForge.FunctionalRequirements"].value)
    assert len(functional["requirements"]) == 3 and "pause" not in json.dumps(functional).lower()
    ids = [r["id"] for r in functional["requirements"]]
    print("requirement ids:", ids)
    assert all(i in text for i in ids), ids  # identifiers come from the document (1.1 .. 1.3), none are invented
    assert "30 days" not in text  # the first draft has no pause requirement

    # nothing changed: a second run makes no LLM call at all
    again = extract_file(PATH, extractor)
    assert all(r.outcome in (ExtractionOutcome.SKIPPED_UNCHANGED_CHUNKS, ExtractionOutcome.SKIPPED_SCOPE) for r in again), format_reports(PATH, again)

    # a new revision arrives: CHANGED, version 2 in DocStore; only the entities whose chunks changed are extracted again
    assert _store(CORPUS / "revisions" / SRS, incoming).outcome.value == "CHANGED"
    revised_reports = extract_file(PATH, extractor)
    print(format_reports(PATH, revised_reports))
    revised = facts.get_fact("ReadmeForge.FunctionalRequirements")
    assert revised.version == 2 and "30 days" in revised.value, revised.value
    assert len(json.loads(revised.value)["requirements"]) == 4
    assert [h["Version"] for h in db.list_fact_history("ReadmeForge.FunctionalRequirements")] == [2]
