"""The generator tool package: search and read knowledge, read documents, save document bodies. Thin typed wrappers over the index, the read
functions and the document savers.

No entity savers (the generator never changes knowledge), no file-moving tools, and no savers for DocumentControl or RevisionHistory (the
caller supplies those). Document savers take no metadata, so nothing here is attributed to the model.
"""
import re
from typing import Annotated

from pydantic import Field, WithJsonSchema

from docfactory import bundle, documents
from docfactory import facts as fact_reads
from docfactory.base_saver import BaseSaver
from docfactory.models.document_record import DocumentRecord
from docfactory.models.fact_record import FactRecord
from docfactory.models.retrieval_hit import RetrievalHit
from docfactory.models.save_result import SaveResult
from docfactory.retrieval.okf_links import bundle_links, fact_key_of_link
from docfactory.retrieval.vector_index import VectorIndex
from docfactory.saver_resolution import document_saver_classes, document_saver_for_key
from docfactory.tools.schema_slim import inline_refs
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

GENERATION_PACKAGE_NAME = "generator"
READ_AND_GENERIC_TOOL_NAMES = ["search_knowledge", "read_okf_file", "get_fact", "list_facts", "get_document", "get_document_schema", "save_document"]


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def document_tool_name(saver_class: type[BaseSaver]) -> str:
    """The tool name of a document body saver: save_ + its model name in snake_case, e.g. save_overview_document."""
    return f"save_{_snake(saver_class.model.__name__)}"


def _doc_type_of(saver_class: type[BaseSaver]) -> str:
    """The document type in the saver's key, e.g. 'SMTD' for '{app}.Outputs.SMTD'."""
    return saver_class.key_patterns[0].rsplit(".", 1)[-1]


def _doc_types() -> dict[str, type[BaseSaver]]:
    return {_doc_type_of(cls): cls for cls in document_saver_classes()}


def _key_help(saver_class: type[BaseSaver]) -> str:
    return " or ".join(f"'{p.replace('{app}', '<App>')}'" for p in saver_class.key_patterns)


def _payload_annotation(saver_class: type[BaseSaver]):
    """A dict argument whose published schema is the document model's schema; validation stays with the saver."""
    schema = saver_class.model.model_json_schema()
    return Annotated[dict, WithJsonSchema(inline_refs(schema, schema.get("$defs", {})))]


def get_document(key: Annotated[str, Field(description="The document key, e.g. 'ReadmeForge.Outputs.SMTD' (the body) or 'ReadmeForge.Outputs.SMTD.DocumentControl'.")]) -> DocumentRecord | None:
    return documents.get_document(key)


def get_document_schema(doc_type: Annotated[str, Field(description="The document type: 'Overview', 'SMTD', 'SRS' or 'SOP'.")]) -> dict:
    saver_class = _doc_types().get(doc_type)
    if saver_class is None:
        raise ValueError(f"unknown document type {doc_type!r}; expected one of {sorted(_doc_types())}")
    schema = saver_class.model.model_json_schema()
    return inline_refs(schema, schema.get("$defs", {}))


def read_okf_file(key: Annotated[str, Field(description="The fact key, e.g. 'ReadmeForge.Architecture' or 'Shared.Kpis'.")]) -> dict:
    fact = fact_reads.get_fact(key)
    if fact is None:
        raise ValueError(f"no fact {key!r}; use search_knowledge or list_facts to find the key")
    path = bundle.bundles_root() / bundle.file_path_of(key).removeprefix(f"{bundle.BUNDLE_DIR}/")
    if not path.exists():
        raise ValueError(f"the knowledge file of {key!r} is not written yet (python -m docfactory.bundle_rebuild writes it)")
    text = path.read_text(encoding="utf-8")
    links = bundle_links(text)
    return {"key": key, "status": fact.status.value, "version": fact.version, "text": text,
            "links": links, "linked_keys": [k for k in map(fact_key_of_link, links) if k]}


def _search_tool(index: VectorIndex):
    def search_knowledge(
        query: Annotated[str, Field(description="What you are looking for, in plain words, e.g. 'deployment environments and hosting'.")],
        app_id: Annotated[str | None, Field(description="Only this application's knowledge plus the shared knowledge, e.g. 'ReadmeForge'. Omit to search everything.")] = None,
        limit: Annotated[int, Field(description="Maximum number of hits.", ge=1, le=30)] = 8,
        include_deprecated: Annotated[bool, Field(description="Also return deprecated facts. Leave false unless you need history.")] = False,
    ) -> list[RetrievalHit]:
        return index.query(query, app_id, limit, include_deprecated)

    return search_knowledge


def _save_document_tool():
    def save_document(
        key: Annotated[str, Field(description="The document body key; it decides the document type, e.g. 'ReadmeForge.Outputs.SMTD'.")],
        payload: Annotated[dict, Field(description="The COMPLETE document body object. Prefer the typed save_<document> tool, whose schema shows the fields.")],
    ) -> SaveResult:
        saver = document_saver_for_key(key)
        if saver is None:
            patterns = sorted(p for cls in document_saver_classes() for p in cls.key_patterns)
            raise ValueError(f"no document saver accepts key {key!r}; keys look like one of: {patterns}")
        return saver.save(key, payload)

    return save_document


def _save_typed_tool(saver_class: type[BaseSaver]):
    saver = saver_class()
    key_type = Annotated[str, Field(description=f"The document body key: {_key_help(saver_class)}. <App> is the application name.")]
    payload_type = _payload_annotation(saver_class)

    def save(key: key_type, payload: payload_type) -> SaveResult:
        return saver.save(key, payload)

    save.__name__ = document_tool_name(saver_class)
    return save


def get_fact(key: Annotated[str, Field(description="The fact key, e.g. 'ReadmeForge.FunctionalRequirements' or 'Shared.Kpis'.")]) -> FactRecord | None:
    return fact_reads.get_fact(key)


def list_facts(app_id: Annotated[str | None, Field(description="Only this application's facts, e.g. 'ReadmeForge'. Omit for all.")] = None) -> list[FactRecord]:
    return fact_reads.list_facts(app_id)


_DESCRIPTIONS = {
    "search_knowledge": "Search the knowledge facts by meaning (over their frontmatter). Returns hits best first with key, title, type, status (stable, draft, deprecated), a stale flag and the knowledge file. Prefer stable facts; mention draft or stale ones you rely on.",
    "read_okf_file": "Read the full knowledge file of one fact by key: its frontmatter and every field, plus any links to other knowledge files. Read-only. Use it on the hits you need; follow links when they are relevant.",
    "get_fact": "Read one stored fact by key (value as JSON, version, completeness, status). Returns null when no such fact exists.",
    "list_facts": "List the stored facts (optionally one application's) with their values. Read-only.",
    "get_document": "Read a stored document row by key (body, .DocumentControl or .RevisionHistory). Returns null when none exists. Use it to see what is already saved before you replace it.",
    "get_document_schema": "The JSON schema of a document type's body, with a description of every field. Call it before building the document: it is the contract.",
    "save_document": "Save a complete document body under its key; the key decides the type. Same effect as the typed save_<document> tools, but without the field schema.",
}


def _typed_description(saver_class: type[BaseSaver]) -> str:
    doc = (saver_class.model.__doc__ or "").strip().splitlines()[0]
    return (f"Save the COMPLETE {saver_class.model.__name__} ({doc}) under key {_key_help(saver_class)}. The whole object replaces the stored one. "
            "Returns ok, the action (CREATED, UPDATED, UNCHANGED or REJECTED) and, when REJECTED, errors with the field, what is expected and the question to answer.")


def generation_tool_names() -> list[str]:
    """The exact tool list of the generator package, in declared order."""
    return [*READ_AND_GENERIC_TOOL_NAMES, *(document_tool_name(cls) for cls in document_saver_classes())]


def build_generation_registry(index: VectorIndex) -> ToolRegistry:
    """A registry holding the generator tools; `search_knowledge` queries `index`."""
    registry = ToolRegistry()
    registry.register(Tool(_search_tool(index), _DESCRIPTIONS["search_knowledge"]))
    registry.register(Tool(read_okf_file, _DESCRIPTIONS["read_okf_file"]))
    for func in (get_fact, list_facts, get_document, get_document_schema):
        registry.register(Tool(func, _DESCRIPTIONS[func.__name__]))
    registry.register(Tool(_save_document_tool(), _DESCRIPTIONS["save_document"]))
    for saver_class in document_saver_classes():
        registry.register(Tool(_save_typed_tool(saver_class), _typed_description(saver_class)))
    return registry


def generation_package(index: VectorIndex) -> ToolPackage:
    """The only tools the document-generator agent may call."""
    return ToolPackage(GENERATION_PACKAGE_NAME, build_generation_registry(index), generation_tool_names())
