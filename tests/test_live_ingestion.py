"""Opt-in live run of the ingestion agent against the corpus: `pytest -m live`.

Uses default_client(): local Ollama (model DOCFACTORY_MODEL, default llama3.2), Ollama Cloud (OLLAMA_HOST + OLLAMA_API_KEY) or
DOCFACTORY_PROVIDER=anthropic. Skipped when the chosen server is not reachable.
"""
import json
import os
import shutil
import urllib.request
from pathlib import Path

import pytest

from docfactory import db
from docfactory.agents.model_client_factory import default_client
from docfactory.agents.ingestion_agent import IngestionAgent
from docfactory.env_file import load_env_file
from docfactory.ingest.paths import DOCSTORE_ENV, INCOMING_ENV

load_env_file()  # live runs take their settings from .env

CORPUS = Path(__file__).parent / "corpus"
SRS = "ReadmeForge SRS v0.3.pdf"

def _llm_available() -> bool:
    if os.environ.get("DOCFACTORY_PROVIDER", "ollama").lower() == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    if not host.startswith("http"):
        host = ("https://" if os.environ.get("OLLAMA_API_KEY") else "http://") + host
    try:
        urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=3)
        return True
    except OSError:
        return False


pytestmark = [pytest.mark.live, pytest.mark.skipif(not _llm_available(), reason="LLM server not reachable")]


def test_agent_classifies_the_corpus(tmp_db, tmp_path, monkeypatch):
    incoming, store = tmp_path / "incoming", tmp_path / "DocStore"
    shutil.copytree(CORPUS / "incoming", incoming)
    monkeypatch.setenv(INCOMING_ENV, str(incoming))
    monkeypatch.setenv(DOCSTORE_ENV, str(store))
    expectations = json.loads((CORPUS / "corpus_expectations.json").read_text(encoding="utf-8"))

    summary = IngestionAgent(default_client()).run()
    print(summary)

    stored = {Path(r["FullPath"]).name: r["FullPath"].split("/")[0] for r in db.list_docstore_rows()}
    for name, expected in expectations.items():
        if name.startswith("revisions/") or expected["outcome"] == "stored or SAME-as-existing":
            continue
        if expected["outcome"] == "deferred":
            assert name not in stored and (incoming / name).is_file(), name
        else:
            assert stored.get(name) == expected["scope"], (name, stored)

    # a new revision of the SRS arrives: same name, new bytes -> CHANGED, version 2
    shutil.copyfile(CORPUS / "revisions" / SRS, incoming / SRS)
    IngestionAgent(default_client()).run()
    assert db.get_docstore_row(f"ReadmeForge/{SRS}")["Version"] == 2
