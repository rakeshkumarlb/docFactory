"""Where the document states an item: the lines of the chunks that name it. Deterministic, no LLM.

An item that is only a name in a list (a component, a hardware class) says nothing else in its fields; its evidence is what answers "why does this
file exist": the heading trail, the chunk number and the line of the document that names it, with the line before it when that line is a list entry
(the group it was listed under). Code sets the item's `evidence`; whatever the model wrote there is replaced.
"""
from pydantic import BaseModel

from docfactory.extract.grounding import normal_identity, normalize
from docfactory.extract.model_shapes import identity_field, item_model
from docfactory.models.doc_chunk import DocChunk

MAX_PLACES = 3
MAX_CHARS = 300
LIST_MARKERS = ("-", "•", "*", "–")


def _entry(chunk: DocChunk, lines: list[str], index: int) -> str:
    line = " ".join(lines[index].split())
    if index > 0 and (line.startswith(LIST_MARKERS) or line[:1].isdigit()):
        line = f"{' '.join(lines[index - 1].split())} / {line}"
    text = line if len(line) <= MAX_CHARS else line[:MAX_CHARS - 3].rstrip() + "..."
    return f"{chunk.heading} (chunk {chunk.chunk_no}): {text}"


def places_of(identifier: str, batch: list[DocChunk]) -> list[str]:
    """Up to MAX_PLACES entries, in document order, for the lines of `batch` that contain `identifier` (compared ignoring case and spacing)."""
    wanted = normal_identity(identifier)
    found = []
    if not wanted:
        return found
    for chunk in sorted(batch, key=lambda c: c.chunk_no):
        lines = chunk.text.splitlines()
        for index, line in enumerate(lines):
            if wanted in normalize(line) and len(found) < MAX_PLACES:
                found.append(_entry(chunk, lines, index))
    return found


def attach_evidence(model: type[BaseModel], stated: dict, batch: list[DocChunk]) -> dict:
    """`stated` with the `evidence` of every item (of a list whose item model has the field) set from the lines of `batch` that name it."""
    result = dict(stated)
    for name, field in model.model_fields.items():
        items = item_model(field.annotation)
        if items is None or "evidence" not in items.model_fields or not isinstance(stated.get(name), list):
            continue
        identity = identity_field(items)
        result[name] = [{**item, "evidence": places_of(str(item.get(identity, "")), batch)} for item in stated[name]]
    return result
