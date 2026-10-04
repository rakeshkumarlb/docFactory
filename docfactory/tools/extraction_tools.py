"""The extraction tool package (Phase 3): one single-tool package per extraction call (least privilege).

- `submit_extraction` (package `extraction`): what one batch of an entity's chunks states about that entity, as a partial object,
  plus an optional one-sentence summary.
The tool validates the answer against the entity's partial model (list items keep their mandatory fields) and refuses item
identifiers that do not appear in the batch text or that two items share, returning feedback the model can act on; an accepted answer is appended to the
list the package was built with. It writes nothing: the extraction pipeline merges, stores and saves.
"""
from typing import Annotated

from pydantic import BaseModel, Field, WithJsonSchema

from docfactory.extract.grounding import duplicate_identities, unknown_identities
from docfactory.extract.partial_schema import partial_model, partial_values
from docfactory.tools.schema_slim import inline_refs
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

EXTRACTION_PACKAGE_NAME = "extraction"
EXTRACTION_TOOL_NAMES = ["submit_extraction"]

Accepted = list[tuple[dict, str | None]]  # (the stated fields, the summary) of every accepted call, in order


def partial_json_schema(entity_model: type[BaseModel]) -> dict:
    """The published schema of the partial object: the entity's fields, all optional, references inlined, token noise dropped."""
    schema = partial_model(entity_model).model_json_schema()
    return inline_refs(schema, schema.get("$defs", {}))


def _submit_tool(entity_model: type[BaseModel], text: str, accepted: Accepted):
    values_type = Annotated[dict, WithJsonSchema(partial_json_schema(entity_model)),
                            Field(description=f"What the chunks state about the {entity_model.__name__}: only the fields they give, values in the document's own words. {{}} when they state nothing.")]

    def submit_extraction(
        values: values_type,
        summary: Annotated[str | None, Field(description="ONE sentence saying what these chunks tell about the entity, e.g. 'Functional requirements for user registration and login.' Omit if they state nothing.")] = None,
    ) -> dict:
        stated, errors = partial_values(entity_model, values)
        if errors:
            return {"ok": False, "errors": [e.model_dump(mode="json", exclude_none=True) for e in errors]}
        duplicates = duplicate_identities(entity_model, stated)
        if duplicates:
            return {"ok": False, "error": f"several items share an identifier: {'; '.join(duplicates)}. Each item needs its own identifier: "
                                          "the one the document gives it, or else its own name or the start of its own statement as written."}
        unknown = unknown_identities(entity_model, stated, text)
        if unknown:
            return {"ok": False, "error": f"these identifiers do not appear in the chunks: {'; '.join(unknown)}. "
                                          "Use each item's identifier exactly as the document writes it, or leave the item out."}
        accepted.append((stated, summary.strip() if summary and summary.strip() else None))
        return {"ok": True, "fields": sorted(stated)}

    return submit_extraction


def extraction_package(entity_model: type[BaseModel], text: str, accepted: Accepted) -> ToolPackage:
    """The only tool of one extraction call over `text` (a batch of chunks); accepted answers are appended to `accepted`."""
    registry = ToolRegistry()
    registry.register(Tool(_submit_tool(entity_model, text, accepted),
                           f"Submit what the chunks state about the {entity_model.__name__}. Call it once; if it returns errors, fix exactly what they name and call again."))
    return ToolPackage(EXTRACTION_PACKAGE_NAME, registry, EXTRACTION_TOOL_NAMES)
