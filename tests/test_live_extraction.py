"""Opt-in live run of the extraction agent against the corpus SRS and its revision: `pytest -m live`.

DocStore is filled deterministically with ingest_operations (no LLM); only the extraction is live. Uses default_client() like the
ingestion live test (local Ollama, Ollama Cloud, or DOCFACTORY_PROVIDER=anthropic). The extraction agent needs a large context:
set DOCFACTORY_NUM_CTX (e.g. 65536) for Ollama. Skipped when the chosen server is not reachable.
"""
import json
import shutil
from pathlib import Path

import pytest

from docfactory import bundle, db, facts, okf_check
from docfactory.agents.extraction_agent import ExtractionAgent
from docfactory.agents.model_client_factory import default_client
from docfactory.ingest import ingest_operations as ops
from docfactory.ingest.paths import DOCSTORE_ENV, INCOMING_ENV
from tests.test_live_ingestion import _llm_available  # also loads .env

CORPUS = Path(__file__).parent / "corpus"
SRS = "ReadmeForge SRS v0.3.pdf"
PATH = f"ReadmeForge/{SRS}"
EXPECTED_KEYS = {"ReadmeForge.ApplicationOverview", "ReadmeForge.FunctionalRequirements", "ReadmeForge.NonFunctionalRequirements"}

pytestmark = [pytest.mark.live, pytest.mark.skipif(not _llm_available(), reason="LLM server not reachable")]


def _store(source: Path, incoming: Path):
    shutil.copyfile(source, incoming / SRS)
    return ops.store_file(SRS, PATH)


def test_agent_extracts_the_srs_and_then_its_revision(tmp_db, tmp_path, monkeypatch):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    monkeypatch.setenv(INCOMING_ENV, str(incoming))
    monkeypatch.setenv(DOCSTORE_ENV, str(tmp_path / "DocStore"))
    assert _store(CORPUS / "incoming" / SRS, incoming).action.value == "NEW"
    text = ops.read_docstore_text(PATH)

    summary = ExtractionAgent(default_client()).run(PATH)
    print(summary)

    stored = {fact.key: fact for fact in facts.list_facts()}
    assert stored, "the agent saved no fact"
    assert set(stored) <= EXPECTED_KEYS | {k for k in stored if k.startswith("ReadmeForge.")}, list(stored)  # only this application's facts
    assert {"ReadmeForge.FunctionalRequirements", "ReadmeForge.NonFunctionalRequirements"} <= set(stored), list(stored)
    for fact in stored.values():
        assert fact.status.value == "draft" and fact.verified == [] and fact.generated_by.startswith("okf-extraction-agent/"), fact.key
        assert f'resource: "{PATH}"' in fact.frontmatter, fact.key  # the agent named the file it read
    assert okf_check.check_bundle(bundle.bundles_root()) == []

    functional = json.loads(stored["ReadmeForge.FunctionalRequirements"].value)
    assert len(functional["requirements"]) == 3 and "pause" not in json.dumps(functional).lower()
    ids = [r["id"] for r in functional["requirements"]]
    print("requirement ids:", ids)
    assert all(i in text for i in ids), ids  # identifiers come from the document (1.1 .. 1.3), none are invented
    assert "30 days" not in text  # the first draft has no pause requirement

    # a new revision arrives: CHANGED, version 2 in DocStore; the agent updates the facts it affects
    assert _store(CORPUS / "revisions" / SRS, incoming).action.value == "CHANGED"
    ExtractionAgent(default_client()).run(PATH)
    revised = facts.get_fact("ReadmeForge.FunctionalRequirements")
    assert revised.version == 2 and "30 days" in revised.value, revised.value
    assert len(json.loads(revised.value)["requirements"]) == 4
    assert [h["Version"] for h in db.list_fact_history("ReadmeForge.FunctionalRequirements")] == [2]
