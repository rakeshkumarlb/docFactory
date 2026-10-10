"""Structure rules for the Phase 2 folders (tools/, agents/, ingest/), which the models/savers checker does not cover.

One class per file, named after the file in snake_case; a module of plain functions may define no class; a Pydantic model never
lives here (those belong in models/); every custom skill and agent keeps the docfactory- prefix (tested elsewhere).
"""
import ast
import re
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "docfactory"
FOLDERS = ("tools", "agents", "ingest", "ingest/chunkers", "ontology", "extract", "generation")
FILES = sorted(p for folder in FOLDERS for p in (PACKAGE / folder).glob("*.py") if p.name != "__init__.py")

# Function-only modules and entry points: they define no class, so the file name carries no class name.
FUNCTION_MODULES = {"docstore_reads", "ingestion_tools", "paths", "file_hash", "target_rules",
                    "run_ingestion", "model_client_factory", "extraction_tools", "prompt_file", "run_extraction",
                    "schema_slim", "needs_tools",
                    "bindings", "template_check", "template_loader", "document_store", "build_body", "template_gaps", "revision_sources", "render_document", "generate_document",
                    "gaps", "document_control", "revision_history", "fallback_needs", "generation_steps",
                    "batching", "fact_keys", "partial_schema", "model_shapes", "grounding", "merge", "missing_questions", "extraction_pipeline", "priority_keywords",
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
