"""The discovery tool package: one single-tool package per discovery call (least privilege).

- `submit_discovery` (package `discovery`): what to keep from chunks that no knowledge entity claims, as notes, and which of the chunks hold
  nothing worth keeping.
The tool checks the answer and returns feedback the model can act on: only the chunks it was given, every given chunk either in a note or
declared worthless, no two notes with one title, every note says something that is in its chunks. An accepted answer is appended to the list the
package was built with. It writes nothing: the discovery pipeline merges and stores.
"""
import re
from typing import Annotated

from pydantic import Field, WithJsonSchema

from docfactory.extract.grounding import normalize
from docfactory.models.note_draft import NoteDraft
from docfactory.tools.schema_slim import inline_refs
from docfactory.tools.tool import Tool
from docfactory.tools.tool_package import ToolPackage
from docfactory.tools.tool_registry import ToolRegistry

DISCOVERY_PACKAGE_NAME = "discovery"
DISCOVERY_TOOL_NAMES = ["submit_discovery"]
WORD = re.compile(r"[a-z0-9]+")
WORD_SHARE = 0.7

Accepted = list[tuple[list[NoteDraft], list[int]]]  # (the notes, the chunk numbers with nothing to keep) of every accepted call, in order


def _notes_schema() -> dict:
    schema = NoteDraft.model_json_schema()
    return {"type": "array", "items": inline_refs(schema, schema.get("$defs", {}))}


def in_text(statement: str, text: str) -> bool:
    """True when `statement` appears in `text` or most of its longer words do (a statement may be lightly rephrased)."""
    wanted, haystack = normalize(statement), normalize(text)
    if wanted in haystack:
        return True
    words = [w for w in WORD.findall(wanted) if len(w) > 3]
    return not words or sum(w in haystack for w in words) / len(words) >= WORD_SHARE


def discovery_errors(notes: list[NoteDraft], nothing: list[int], asked: set[int], text: str) -> list[str]:
    """What is wrong with the answer, as sentences the model can act on; empty when it is acceptable."""
    errors = []
    unknown = sorted(({n for note in notes for n in note.chunks} | set(nothing)) - asked)
    if unknown:
        errors.append(f"these chunk numbers were not given to you: {unknown}; use only {sorted(asked)}")
    titles = [normalize(note.title) for note in notes]
    errors += [f"two notes share the title {t!r}: give each its own title or merge them" for t in sorted({t for t in titles if titles.count(t) > 1})]
    for note in notes:
        if not note.summary.strip() and not note.statements:
            errors.append(f"note {note.title!r} has neither a summary nor statements: say what the passage holds")
        for statement in note.statements:
            if not in_text(statement, text):
                errors.append(f"note {note.title!r}: the statement {statement[:80]!r} is not in the chunks; copy what the chunks say")
    both = sorted({n for note in notes for n in note.chunks} & set(nothing))
    if both:
        errors.append(f"chunks {both} are both in a note and listed as holding nothing: choose one")
    uncovered = sorted(asked - {n for note in notes for n in note.chunks} - set(nothing))
    if uncovered:
        errors.append(f"chunks {uncovered} are in no note and not listed in nothing_to_keep: write a note for them or list them")
    return errors


def _submit_tool(asked: set[int], text: str, accepted: Accepted):
    notes_type = Annotated[list[NoteDraft], WithJsonSchema(_notes_schema()),
                           Field(description="One note per passage worth keeping. Use [] when none of the chunks holds anything worth keeping.")]
    nothing_type = Annotated[list[int] | None, Field(description="Numbers of the chunks that hold nothing worth keeping (page furniture, blank or repeated text). Omit when none.")]

    def submit_discovery(notes: notes_type, nothing_to_keep: nothing_type = None) -> dict:
        nothing = sorted(set(nothing_to_keep or []))
        errors = discovery_errors(notes, nothing, asked, text)
        if errors:
            return {"ok": False, "errors": errors}
        accepted.append((notes, nothing))
        return {"ok": True, "notes": len(notes)}

    return submit_discovery


def discovery_package(asked: set[int], text: str, accepted: Accepted) -> ToolPackage:
    """The only tool of one discovery call over `text` (chunks numbered `asked`); accepted answers are appended to `accepted`."""
    registry = ToolRegistry()
    registry.register(Tool(_submit_tool(asked, text, accepted),
                           "Submit the notes to keep from these chunks and the chunks that hold nothing worth keeping. Call it once; if it returns errors, fix exactly what they name and call again."))
    return ToolPackage(DISCOVERY_PACKAGE_NAME, registry, DISCOVERY_TOOL_NAMES)
