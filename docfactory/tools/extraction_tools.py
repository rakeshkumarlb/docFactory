"""The extraction tool package: read DocStore text, read stored facts, save facts. Thin typed wrappers over the savers and read functions.

No file-moving tools and no document savers (least privilege). The actor recorded as `generated.by` is fixed when the package is built, so
the model cannot choose or forge it, and each source's `last_modified` comes from the DocStore row, not from the model.
"""
import re
from typing import Annotated

from pydantic import Field, WithJsonSchema

from docfactory import db, facts
from docfactory.base_saver import BaseSaver
from docfactory.ingest import docstore_reads as ops
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord
from docfactory.models.fact_source import FactSource
from docfactory.models.save_result import SaveResult
from docfactory.saver_resolution import entity_saver_classes, saver_for_key
from docfactory.tools.schema_slim import inline_refs
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

EXTRACTION_PACKAGE_NAME = "extraction"
READ_AND_GENERIC_TOOL_NAMES = ["list_docstore", "read_docstore_text", "get_fact", "list_facts", "save_fact"]

DocStorePath = Annotated[str, Field(description="Path of a file in DocStore/, relative with forward slashes, e.g. 'ReadmeForge/ReadmeForge SRS v0.3.pdf'.")]
Title = Annotated[str | None, Field(description="Display name of the fact, e.g. 'ReadmeForge functional requirements'. Omit to let the code derive it from the key.")]
Description = Annotated[str | None, Field(description="ONE sentence summarizing what this fact says, for search snippets. Omit if you cannot summarize it truthfully.")]
Tags = Annotated[list[str] | None, Field(description="Short cross-cutting categorization strings, e.g. ['requirements', 'srs'].")]
Sources = Annotated[list[str] | None, Field(description="The DocStore paths this fact was extracted from, exactly as list_docstore shows them, e.g. ['ReadmeForge/ReadmeForge SRS v0.3.pdf']. Always name the file you read.")]
StaleAfter = Annotated[str | None, Field(description="ISO 8601 datetime with explicit UTC offset after which the fact should be re-checked, e.g. '2027-01-01T00:00:00Z'. Omit unless the document states an expiry.")]


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _payload_annotation(saver_class: type[BaseSaver]):
    """A dict argument whose published schema is the fact's model schema (descriptions included); validation stays with the saver."""
    schema = saver_class.model.model_json_schema()
    return Annotated[dict, WithJsonSchema(inline_refs(schema, schema.get("$defs", {})))]


def _key_help(saver_class: type[BaseSaver]) -> str:
    patterns = [p.replace("{app}", "<App>").replace("{component}", "<Component>") for p in saver_class.key_patterns]
    return " or ".join(f"'{p}'" for p in patterns)


def _source(path: str) -> FactSource:
    row = db.get_docstore_row(path.replace("\\", "/").strip("/"))
    if row is None:
        raise ValueError(f"source {path!r} is not in the DocStore; use list_docstore and name the file exactly as it is listed")
    return FactSource(resource=row["FullPath"], last_modified=row["Timestamp"])


def _save(saver: BaseSaver, actor: str, key: str, payload: dict, title, description, tags, sources, stale_after) -> SaveResult:
    meta = FactMeta(generated_by=actor, title=title, description=description, tags=tags or [],
                    sources=[_source(path) for path in sources or []], stale_after=stale_after)
    return saver.save(key, payload, meta=meta)


def list_docstore(
    folder: Annotated[str | None, Field(description="Only files at or below this DocStore folder, e.g. 'ReadmeForge'. Omit to list everything.")] = None,
    name_contains: Annotated[str | None, Field(description="Case-insensitive text that must appear in the stored path, e.g. 'srs'.")] = None,
) -> list[dict]:
    return ops.search_docstore(folder, name_contains)


def read_docstore_text(path: DocStorePath) -> str:
    return ops.read_docstore_text(path)


def get_fact(key: Annotated[str, Field(description="The fact key, e.g. 'ReadmeForge.FunctionalRequirements' or 'Shared.Kpis'.")]) -> FactRecord | None:
    return facts.get_fact(key)


def list_facts(app_id: Annotated[str | None, Field(description="Only this application's facts, e.g. 'ReadmeForge'. Omit for all.")] = None) -> list[FactRecord]:
    return facts.list_facts(app_id)


def _save_fact_tool(actor: str):
    def save_fact(
        key: Annotated[str, Field(description="The fact key; it decides which entity the payload must be, e.g. 'ReadmeForge.Architecture'.")],
        payload: Annotated[dict, Field(description="The COMPLETE fact object. Prefer the typed save_<entity> tool, whose schema shows the fields.")],
        title: Title = None, description: Description = None, tags: Tags = None, sources: Sources = None, stale_after: StaleAfter = None,
    ) -> SaveResult:
        saver = saver_for_key(key)
        if saver is None:
            patterns = sorted({p for cls in entity_saver_classes() for p in cls.key_patterns})
            raise ValueError(f"no entity saver accepts key {key!r}; keys look like one of: {patterns}")
        return _save(saver, actor, key, payload, title, description, tags, sources, stale_after)

    return save_fact


def _save_entity_tool(saver_class: type[BaseSaver], actor: str):
    saver = saver_class()
    key_type = Annotated[str, Field(description=f"The fact key: {_key_help(saver_class)}. <App> is the application name as in the DocStore folder; <Component> is free text.")]
    payload_type = _payload_annotation(saver_class)

    def save(key: key_type, payload: payload_type, title: Title = None, description: Description = None, tags: Tags = None,
             sources: Sources = None, stale_after: StaleAfter = None) -> SaveResult:
        return _save(saver, actor, key, payload, title, description, tags, sources, stale_after)

    save.__name__ = entity_tool_name(saver_class)
    return save


def entity_tool_name(saver_class: type[BaseSaver]) -> str:
    """The tool name of an entity saver: save_ + its model name in snake_case."""
    return f"save_{_snake(saver_class.model.__name__)}"


_DESCRIPTIONS = {
    "list_docstore": "List the files stored in DocStore (path, version, SHA-256, timestamp). Read-only. Use it to find the exact path to read and to cite as a source.",
    "read_docstore_text": "Read the text of one stored original (PDF, Word and HTML are read from their text version). Read-only.",
    "get_fact": "Read one stored fact by key, with its version, completeness and status. Returns null when no such fact exists. Call it before saving, so you send the complete merged object.",
    "list_facts": "List the stored facts (optionally one application's) with their values. Read-only. Use it to see what already exists.",
    "save_fact": "Save a complete fact under its key; the key decides the entity. Same effect as the typed save_<entity> tools, but without the field schema.",
}


def _entity_description(saver_class: type[BaseSaver]) -> str:
    doc = (saver_class.model.__doc__ or "").strip().splitlines()[0]
    return (f"Save the COMPLETE {saver_class.model.__name__} fact ({doc}) under key {_key_help(saver_class)}. The whole object replaces the stored one, "
            "so call get_fact first when it may exist and send the merged result. Returns ok, the action (CREATED, UPDATED, UNCHANGED or REJECTED) and, "
            "when REJECTED, errors with the field, what is expected and the question to answer.")


def extraction_tool_names() -> list[str]:
    """The exact tool list of the extraction package, in declared order."""
    return [*READ_AND_GENERIC_TOOL_NAMES, *(entity_tool_name(cls) for cls in entity_saver_classes())]


def build_extraction_registry(actor: str) -> ToolRegistry:
    """A registry holding the extraction tools; saved facts record `actor` as generated.by."""
    registry = ToolRegistry()
    for func in (list_docstore, read_docstore_text, get_fact, list_facts):
        registry.register(Tool(func, _DESCRIPTIONS[func.__name__]))
    registry.register(Tool(_save_fact_tool(actor), _DESCRIPTIONS["save_fact"]))
    for saver_class in entity_saver_classes():
        registry.register(Tool(_save_entity_tool(saver_class, actor), _entity_description(saver_class)))
    return registry


def extraction_package(actor: str) -> ToolPackage:
    """The only tools the extraction agent may call."""
    return ToolPackage(EXTRACTION_PACKAGE_NAME, build_extraction_registry(actor), extraction_tool_names())
