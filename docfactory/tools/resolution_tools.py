"""The resolution tool package: one single-tool package per resolution call (least privilege).

- `submit_merges` (package `resolution`): the groups of entities, among the listed entities of one type, that are the same thing.
The tool refuses: an id that is not in the list, a group whose kept id is also among its 'same' ids or that has no 'same' id, and an id in two
groups. An accepted answer is appended to the list the package was built with. It writes nothing.
"""
from typing import Annotated

from pydantic import Field, WithJsonSchema

from docfactory.models.resolution_group import ResolutionGroup
from docfactory.tools.schema_slim import inline_refs
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

RESOLUTION_PACKAGE_NAME = "resolution"
RESOLUTION_TOOL_NAMES = ["submit_merges"]

Accepted = list[list[ResolutionGroup]]


def _groups_schema() -> dict:
    schema = ResolutionGroup.model_json_schema()
    return {"type": "array", "items": inline_refs(schema, schema.get("$defs", {}))}


def merge_errors(groups: list[ResolutionGroup], ids: set[str]) -> list[str]:
    """What is wrong with `groups` for the listed entity `ids`; empty when they can be accepted."""
    errors, seen = [], set()
    for group in groups:
        members = [group.keep, *group.same]
        unknown = [m for m in members if m not in ids]
        if unknown:
            errors.append(f"group {group.keep!r}: {unknown} are not ids of the listed entities; use the ids exactly as listed")
        if not group.same:
            errors.append(f"group {group.keep!r}: no 'same' ids; leave out groups of one entity")
        if group.keep in group.same:
            errors.append(f"group {group.keep!r}: the kept id is also in 'same'")
        twice = sorted(set(members) & seen)
        if twice:
            errors.append(f"group {group.keep!r}: {twice} are already in another group; put each entity in one group only")
        seen |= set(members)
    return errors


def _submit_tool(ids: set[str], accepted: Accepted):
    groups_type = Annotated[list[ResolutionGroup], WithJsonSchema(_groups_schema()),
                            Field(description="The groups of listed entities that are the same thing. [] when every entity is a different thing.")]

    def submit_merges(groups: groups_type) -> dict:
        errors = merge_errors(groups, ids)
        if errors:
            return {"ok": False, "errors": errors}
        accepted.append(list(groups))
        return {"ok": True, "groups": len(groups)}

    return submit_merges


def resolution_package(ids: set[str], accepted: Accepted) -> ToolPackage:
    """The only tool of one resolution call over the listed entity `ids`; an accepted answer is appended to `accepted`."""
    registry = ToolRegistry()
    registry.register(Tool(_submit_tool(ids, accepted),
                           "Submit the groups of entities that are the same thing. Call it once; if it returns errors, fix exactly what they name and call again."))
    return ToolPackage(RESOLUTION_PACKAGE_NAME, registry, RESOLUTION_TOOL_NAMES)
