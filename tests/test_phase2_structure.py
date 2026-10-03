"""Structure rules for the Phase 2 folders (tools/, agents/, ingest/), which the models/savers checker does not cover.

One class per file, named after the file in snake_case; a module of plain functions may define no class; a Pydantic model never
lives here (those belong in models/); every custom skill and agent keeps the docfactory- prefix (tested elsewhere).
"""
import ast
import re
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "docfactory"
FOLDERS = ("tools", "agents", "ingest", "ingest/chunkers", "retrieval", "ontology")
FILES = sorted(p for folder in FOLDERS for p in (PACKAGE / folder).glob("*.py") if p.name != "__init__.py")

# Function-only modules and entry points: they define no class, so the file name carries no class name.
FUNCTION_MODULES = {"ingestion_tools", "ingest_operations", "paths", "file_hash", "text_extraction", "target_rules",
                    "run_ingestion", "model_client_factory", "sidecar_rebuild", "extraction_tools", "prompt_file", "run_extraction",
                    "generation_tools", "run_generation",
                    "embedder_factory", "frontmatter_values", "okf_links", "index_rebuild",
                    "signals", "ontology_render",
                    "chunking", "tagging", "scope_rules", "pipeline", "chunk_rebuild", "pdf_chunker", "word_chunker", "html_chunker", "text_chunker"}


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_one_class_per_file_named_after_the_file(path):
    classes = [n for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, ast.ClassDef)]
    if path.stem in FUNCTION_MODULES:
        assert not classes, f"{path.name} is a function module and must define no class"
        return
    assert len(classes) == 1, f"{path.name} must define exactly one class (found {[c.name for c in classes]})"
    assert _snake(classes[0].name) == path.stem


@pytest.mark.parametrize("path", FILES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_no_pydantic_models_outside_models_folder(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ClassDef):
            bases = {getattr(b, "id", getattr(b, "attr", "")) for b in node.bases}
            assert not bases & {"BaseModel", "DocFactoryModel"}, f"{node.name} must live in models/"


def test_every_phase2_module_is_accounted_for():
    stems = {p.stem for p in FILES}
    assert FUNCTION_MODULES <= stems, f"stale entries: {FUNCTION_MODULES - stems}"


def test_the_ingestion_package_has_exactly_the_agreed_tools():
    """Least privilege: the ingestion package has exactly the agreed tools (the extraction package is pinned in test_extraction_tools.py)."""
    from docfactory.tools.ingestion_tools import ingestion_package

    assert ingestion_package().tool_names() == ["list_incoming", "read_incoming_text", "search_docstore",
                                                "compare_with_docstore", "store_file", "defer_file"]
