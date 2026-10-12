"""The type-proposal tool package: one single-tool package per proposal call (least privilege).

- `submit_type_proposal` (package `type-proposal`): zero or more proposed new entity types for chunks the ontology cannot place.
The tool checks every proposal (`proposal_checks`) and returns feedback the model can act on. An accepted answer is appended to the list the package
was built with. It writes nothing: the proposal pipeline stores the proposals, and a separate developer step turns an approved one into a model.
"""
from typing import Annotated

from pydantic import Field, WithJsonSchema

from docfactory.models.type_proposal import TypeProposal
from docfactory.ontology.proposal_checks import proposal_errors
from docfactory.tools.schema_slim import inline_refs
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

PROPOSAL_PACKAGE_NAME = "type-proposal"
PROPOSAL_TOOL_NAMES = ["submit_type_proposal"]
SET_BY_CODE = ("source_path", "proposed_by")

Accepted = list[list[TypeProposal]]  # the proposals of every accepted call, in order


def _proposals_schema() -> dict:
    schema = TypeProposal.model_json_schema()
    item = inline_refs(schema, schema.get("$defs", {}))
    for name in SET_BY_CODE:
        item["properties"].pop(name, None)
    return {"type": "array", "items": item}


def _submit_tool(asked: set[int], accepted: Accepted):
    proposals_type = Annotated[list[TypeProposal], WithJsonSchema(_proposals_schema()),
                               Field(description="The proposed new entity types. Use [] when every chunk fits an existing entity or is not a recurring kind of knowledge.")]

    def submit_type_proposal(proposals: proposals_type) -> dict:
        errors = [f"{p.entity}: {e}" for p in proposals for e in proposal_errors(p, asked)]
        names = [p.entity for p in proposals]
        errors += [f"the entity {n!r} is proposed twice" for n in sorted({n for n in names if names.count(n) > 1})]
        if errors:
            return {"ok": False, "errors": errors}
        accepted.append(proposals)
        return {"ok": True, "proposals": len(proposals)}

    return submit_type_proposal


def proposal_package(asked: set[int], accepted: Accepted) -> ToolPackage:
    """The only tool of one proposal call over chunks numbered `asked`; accepted answers are appended to `accepted`."""
    registry = ToolRegistry()
    registry.register(Tool(_submit_tool(asked, accepted),
                           "Submit the proposed new entity types (or none). Call it once; if it returns errors, fix exactly what they name and call again."))
    return ToolPackage(PROPOSAL_PACKAGE_NAME, registry, PROPOSAL_TOOL_NAMES)
