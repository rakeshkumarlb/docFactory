"""The ingestion fallback tool packages: one single-tool package per fallback call (least privilege).

- `submit_chunk_tags` (package `ingestion-tagging`): the model's tags for the chunks the rules could not tag.
- `submit_scope` (package `ingestion-scope`): the model's scope decision for a file the rules could not place.
Each tool validates the answer (closed entity list, only the chunks that were asked about, a legal scope) and returns feedback the
model can act on; an accepted answer is appended to the list the package was built with. The tools write nothing: the pipeline
decides what is stored.
"""
from typing import Annotated

from pydantic import Field

from docfactory.ingest.scope_rules import GENERAL, SHARED, folder_name
from docfactory.ingest.target_rules import SCOPE_PATTERN
from docfactory.models.chunk_tag_proposal import ChunkTagProposal
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

TAGGING_PACKAGE_NAME = "ingestion-tagging"
SCOPE_PACKAGE_NAME = "ingestion-scope"
TAGGING_TOOL_NAMES = ["submit_chunk_tags"]
SCOPE_TOOL_NAMES = ["submit_scope"]


def _tags_tool(asked: set[int], entities: list[str], accepted: list[list[ChunkTagProposal]]):
    def submit_chunk_tags(
        tags: Annotated[list[ChunkTagProposal], Field(description="One entry per chunk you were asked about: its chunk_no, the entities it informs (possibly none) and a short reason.")],
    ) -> dict:
        problems = [f"chunk {t.chunk_no} was not asked about" for t in tags if t.chunk_no not in asked]
        problems += [f"chunk {t.chunk_no}: unknown entity {e!r}" for t in tags for e in t.entities if e not in entities]
        missing = sorted(asked - {t.chunk_no for t in tags})
        if missing:
            problems.append(f"no answer for chunks {missing}: give every asked chunk an entry (an empty entities list means none)")
        if problems:
            raise ValueError("; ".join(problems) + f". Valid entities: {', '.join(entities)}")
        accepted.append(list(tags))
        return {"ok": True, "accepted": len(tags)}

    return submit_chunk_tags


def _scope_tool(accepted: list[tuple[str | None, str]]):
    def submit_scope(
        scope: Annotated[str | None, Field(description="The application name the document is about (as written in it), 'shared' for a standard common to many applications, 'general' for documentation of no single application, or null when you are not sure.")],
        reason: Annotated[str, Field(description="One short sentence quoting what in the document decided it, or why you are not sure.", min_length=1)],
    ) -> dict:
        if scope is not None:
            scope = scope.strip()
            folder = scope.lower() if scope.lower() in (SHARED, GENERAL) else folder_name(scope)
            if not folder or not SCOPE_PATTERN.match(folder):
                raise ValueError(f"{scope!r} cannot be a folder name; give the application name as written, 'shared', 'general' or null")
            scope = folder
        accepted.append((scope, reason.strip()))
        return {"ok": True, "scope": scope}

    return submit_scope


def tagging_package(asked: set[int], entities: list[str], accepted: list[list[ChunkTagProposal]]) -> ToolPackage:
    """The only tool of the tagging fallback; accepted answers are appended to `accepted`."""
    registry = ToolRegistry()
    registry.register(Tool(_tags_tool(asked, entities, accepted),
                           "Submit the entity tags for the chunks you were asked about. Call it once with every chunk; fix and call again if it returns an error."))
    return ToolPackage(TAGGING_PACKAGE_NAME, registry, TAGGING_TOOL_NAMES)


def scope_package(accepted: list[tuple[str | None, str]]) -> ToolPackage:
    """The only tool of the scope fallback; accepted answers are appended to `accepted`."""
    registry = ToolRegistry()
    registry.register(Tool(_scope_tool(accepted), "Submit the scope (DocStore folder) of the document, or null when you are not sure."))
    return ToolPackage(SCOPE_PACKAGE_NAME, registry, SCOPE_TOOL_NAMES)
