"""Opt-in live run of the document-generator agent over the seeded ReadmeForge facts: `pytest -m live tests/test_live_generation.py`.

Facts are saved deterministically from the samples (no LLM) and the index is built with the real embedder (Ollama /api/embed,
DOCFACTORY_EMBED_MODEL); only the generation is live. The generated Overview body is compared with the deterministic `build_document`
result: it must say nothing the facts do not say. Skipped when the chat server or the embedding model is not reachable.
"""
import json
from pathlib import Path

import pytest

from docfactory import documents
from docfactory.agents.generator_agent import GeneratorAgent
from docfactory.agents.model_client_factory import default_client
from docfactory.build import build_document
from docfactory.documentmodels.documents.overview_document import OverviewDocument
from docfactory.entitysaver.application_overview_saver import ApplicationOverviewSaver
from docfactory.entitysaver.kpis_saver import KpisSaver
from docfactory.models.fact_meta import FactMeta
from docfactory.retrieval.embedder_factory import default_embedder
from docfactory.retrieval.sqlite_vector_index import SqliteVectorIndex
from tests.test_live_ingestion import _llm_available  # also loads .env

SAMPLES = Path(__file__).parent.parent / "samples" / "json"
KEY = "ReadmeForge.Outputs.Overview"

pytestmark = [pytest.mark.live, pytest.mark.skipif(not _llm_available(), reason="LLM server not reachable")]


def _leaves(value) -> set[str]:
    """Every string and number inside a JSON value, as text."""
    if isinstance(value, dict):
        return set().union(*(_leaves(v) for v in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_leaves(v) for v in value)) if value else set()
    return {str(value)} if value not in (None, "") else set()


def _seed():
    meta = FactMeta(generated_by="seed", title="ReadmeForge overview", description="What ReadmeForge is, who owns it and how it is run.")
    for saver, key, folder, name, fact_meta in (
        (ApplicationOverviewSaver(), "ReadmeForge.ApplicationOverview", "application_overview", "readmeforge_full.json", meta),
        (KpisSaver(), "Shared.Kpis", "kpis", "shared_devex_kpis_full.json",
         FactMeta(generated_by="seed", title="Shared developer-experience KPIs", description="KPIs every application reports.")),
    ):
        payload = json.loads((SAMPLES / folder / name).read_text(encoding="utf-8"))
        assert saver.save(key, payload, meta=fact_meta).ok


def test_agent_generates_the_overview_from_the_knowledge(tmp_db):
    _seed()
    try:
        index = SqliteVectorIndex(default_embedder())
        assert index.rebuild() == (2, 0)
    except RuntimeError as error:
        pytest.skip(f"embedding model not available: {error}")
    hits = index.query("what the application is and its KPIs", app_id="ReadmeForge")
    print([(h.key, h.score) for h in hits])
    assert {h.key for h in hits} == {"ReadmeForge.ApplicationOverview", "Shared.Kpis"}

    summary = GeneratorAgent(default_client(), index).run("ReadmeForge", "Overview")
    print(summary)

    record = documents.get_document(KEY)
    assert record is not None, "the agent saved no Overview"
    expected, _ = build_document(OverviewDocument, "ReadmeForge")
    generated = json.loads(record.value)
    expected_json = json.loads(expected.model_dump_json())
    unsupported = _leaves(generated) - _leaves(expected_json)
    print("completeness:", record.completeness, "of", "deterministic body")
    assert not unsupported, f"values no stored fact states: {sorted(unsupported)}"
    assert record.completeness > 0
