"""Requirement priorities from the requirement's own wording (Phase 3). Deterministic, no LLM.

Requirement documents mark obligation with keywords in the RFC 2119 sense: SHALL / MUST (also SHALL NOT, MUST NOT, REQUIRED) is
mandatory, SHOULD (RECOMMENDED) is advised, MAY (OPTIONAL) is permitted. A requirement item whose priority the model left empty
gets the priority its own statement states: MUST, SHOULD or COULD, the strongest keyword winning. MAY and OPTIONAL count only in
capitals, since 'may' is ordinary English. A priority the model gave is never changed, and an item without a keyword stays empty.
"""
import re
from typing import get_args

from pydantic import BaseModel

from docfactory.entitymodels.items.requirement_priority import RequirementPriority
from docfactory.extract.model_shapes import item_model

STATEMENT_FIELDS = ("description", "statement")  # where a requirement item holds the document's own sentence
_KEYWORDS = [
    (RequirementPriority.MUST, re.compile(r"\b(shall|must|required)\b", re.IGNORECASE)),
    (RequirementPriority.SHOULD, re.compile(r"\b(should|recommended)\b", re.IGNORECASE)),
    (RequirementPriority.COULD, re.compile(r"\b(MAY|OPTIONAL)\b")),
]


def keyword_priority(text: str) -> RequirementPriority | None:
    """The priority the strongest obligation keyword in `text` states, or None."""
    return next((priority for priority, pattern in _KEYWORDS if pattern.search(text)), None)


def _has_priority(model: type[BaseModel]) -> bool:
    field = model.model_fields.get("priority")
    return field is not None and RequirementPriority in (get_args(field.annotation) or (field.annotation,))


def fill_priorities(model: type[BaseModel], data: dict) -> tuple[dict, int]:
    """(a copy of `data` with empty item priorities filled from their statements' keywords, how many were filled)."""
    out, filled = dict(data), 0
    for name, field in model.model_fields.items():
        items = item_model(field.annotation)
        if items is None or not _has_priority(items) or not isinstance(out.get(name), list):
            continue
        new_items = []
        for item in out[name]:
            text = " ".join(str(item[f]) for f in STATEMENT_FIELDS if isinstance(item.get(f), str))
            priority = None if item.get("priority") else keyword_priority(text)
            if priority is not None:
                item = {**item, "priority": priority.value}
                filled += 1
            new_items.append(item)
        out[name] = new_items
    return out, filled
