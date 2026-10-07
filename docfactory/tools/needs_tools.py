"""The needs-list tool package (Phase 4): one single-tool package per needs-list call (least privilege).

- `submit_needs` (package `generation-needs`): the document's needs list, the questions that together cover its numbered gaps.
The tool checks the answer and returns feedback the model can act on: every need names who can answer it and cites at least one gap,
no gap number is unknown, and every gap is covered by at least one need. Only gaps reach the list, so no question is invented.
An accepted answer is appended to the list the package was built with. It writes nothing: generate saves the MissingInfo row.
"""
from typing import Annotated

from pydantic import Field, WithJsonSchema

from docfactory.documentmodels.shared.document_gap import DocumentGap
from docfactory.documentmodels.shared.document_need import DocumentNeed
from docfactory.tools.schema_slim import inline_refs
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

NEEDS_PACKAGE_NAME = "generation-needs"
NEEDS_TOOL_NAMES = ["submit_needs"]


def _needs_schema() -> dict:
    schema = DocumentNeed.model_json_schema()
    return {"type": "array", "minItems": 1, "items": inline_refs(schema, schema.get("$defs", {}))}


def coverage_errors(needs: list[DocumentNeed], gaps: list[DocumentGap]) -> list[str]:
    """What is wrong with `needs` as a cover of `gaps`: needs without audience, unknown gap numbers, gaps no need covers."""
    known = {gap.number for gap in gaps}
    errors = [f"need {i} ({need.question[:60]!r}) names no audience: say who can answer it"
              for i, need in enumerate(needs, start=1) if not need.audience.strip()]
    unknown = sorted({n for need in needs for n in need.gaps} - known)
    if unknown:
        errors.append(f"these gap numbers do not exist: {unknown}; cite only the numbers of the gaps you were given")
    uncovered = sorted(known - {n for need in needs for n in need.gaps})
    if uncovered:
        errors.append(f"these gaps are covered by no need: {uncovered}; add them to a need that asks for them, or add a need")
    return errors


def _submit_tool(gaps: list[DocumentGap], accepted: list[list[DocumentNeed]]):
    needs_type = Annotated[list[DocumentNeed], WithJsonSchema(_needs_schema()),
                           Field(min_length=1, description="The needs list, most important first. Each need: one question in the application's terms "
                                                           "(it may merge related gaps), who can answer it, and the numbers of the gaps it covers.")]

    def submit_needs(needs: needs_type) -> dict:
        errors = coverage_errors(needs, gaps)
        if errors:
            return {"ok": False, "errors": errors}
        accepted.append(list(needs))
        return {"ok": True, "needs": len(needs)}

    return submit_needs


def needs_package(gaps: list[DocumentGap], accepted: list[list[DocumentNeed]]) -> ToolPackage:
    """The only tool of one needs-list call over `gaps`; an accepted needs list is appended to `accepted`."""
    registry = ToolRegistry()
    registry.register(Tool(_submit_tool(gaps, accepted),
                           "Submit the document's needs list covering every gap. Call it once; if it returns errors, fix exactly what they name and call again."))
    return ToolPackage(NEEDS_PACKAGE_NAME, registry, NEEDS_TOOL_NAMES)
