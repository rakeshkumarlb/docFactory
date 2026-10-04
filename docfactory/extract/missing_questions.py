"""The questions a merged fact still leaves open (Phase 3 report). Deterministic, read from the model metadata, never written by hand.

A top-level field that states nothing gives its question; a field left empty in some items of a list gives its question once, with
how many items lack it, so a 28-requirement list without acceptance criteria is one line, not 28.
"""
from pydantic import BaseModel

from docfactory.completeness import is_scored
from docfactory.extract.model_shapes import item_model, question_of
from docfactory.extract.partial_schema import is_empty


def missing_questions(model: type[BaseModel], data: dict) -> list[str]:
    """One line per unanswered field of `data` (a JSON value of `model`): 'field: question' or 'list[].field: question (missing in k of n)'."""
    lines = []
    for name, field in model.model_fields.items():
        if not is_scored(field):
            continue
        value = data.get(name)
        if is_empty(value):
            lines.append(f"{name}: {question_of(field)}")
            continue
        items = item_model(field.annotation)
        if items is None or not isinstance(value, list):
            continue
        for item_name, item_field in items.model_fields.items():
            if not is_scored(item_field):
                continue
            missing = sum(is_empty(item.get(item_name)) for item in value)
            if missing:
                lines.append(f"{name}[].{item_name}: {question_of(item_field)} (missing in {missing} of {len(value)})")
    return lines
