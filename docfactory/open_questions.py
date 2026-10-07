"""The open questions of a validated fact: every scored field still at its default, with its question and the default assumed.

Deterministic, read only from the model definition and the value. It uses the completeness rule (completeness.py): a field is
unanswered when it equals its default or is an empty list; a NotApplicable and a mandatory field are answered. A nested model is
asked about field by field; the fields of list items are asked once per field, with how many items lack them and which (each item named
by its mandatory fields).
"""
import json
from enum import Enum

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from docfactory.completeness import is_scored
from docfactory.models.fact_question import FactQuestion
from docfactory.models.not_applicable import NotApplicable


def question_of(field: FieldInfo) -> str:
    """The field's declared question, else its description."""
    extra = field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}
    return extra.get("question") or field.description or ""


def default_in_words(field: FieldInfo) -> str:
    """The field's default as a reader sees it: empty text, empty list, none, no, yes, an enum value or the JSON of the value."""
    default = field.get_default(call_default_factory=True)
    if default is None:
        return "none"
    if default == "":
        return "empty text"
    if default == []:
        return "empty list"
    if isinstance(default, bool):
        return "yes" if default else "no"
    if isinstance(default, Enum):
        return str(default.value)
    if isinstance(default, BaseModel):
        return default.model_dump_json()
    return json.dumps(default, ensure_ascii=False)


def item_label(item: BaseModel) -> str:
    """An item named by the values of its mandatory fields, joined by ' | ', e.g. 'FR-01 | Login | The system SHALL ...'."""
    values = [getattr(item, name) for name, field in type(item).model_fields.items() if field.is_required()]
    return " | ".join(str(v.value) if isinstance(v, Enum) else str(v) for v in values)


def _unanswered(field: FieldInfo, value) -> bool:
    if isinstance(value, NotApplicable) or field.is_required():
        return False
    return (isinstance(value, list) and not value) or value == field.get_default(call_default_factory=True)


def _walk(model: type[BaseModel], objects: list[BaseModel], prefix: str, in_list: bool, out: list[FactQuestion]) -> None:
    """Questions for `model`'s fields over `objects` (one object, or every item of a list when `in_list`)."""
    for name, field in model.model_fields.items():
        if not is_scored(field):
            continue
        path = f"{prefix}{name}"
        values = [getattr(obj, name) for obj in objects]
        lacking = [obj for obj, value in zip(objects, values) if _unanswered(field, value)]
        if lacking:
            counts = {"missing_in": len(lacking), "item_count": len(objects), "missing_items": [item_label(obj) for obj in lacking]} if in_list else {}
            out.append(FactQuestion(path=path, question=question_of(field), default_assumed=default_in_words(field), **counts))
        present = [v for v in values if not _unanswered(field, v) and not isinstance(v, NotApplicable)]
        nested = [v for v in present if isinstance(v, BaseModel)]
        if nested:
            _walk(type(nested[0]), nested, f"{path}.", in_list, out)
        items = [item for v in present if isinstance(v, list) for item in v if isinstance(item, BaseModel)]
        if items:
            _walk(type(items[0]), items, f"{path}[].", True, out)


def open_questions(fact: BaseModel) -> list[FactQuestion]:
    """The open questions of a validated fact, in model field order. Empty when every scored field is answered."""
    out: list[FactQuestion] = []
    _walk(type(fact), [fact], "", False, out)
    return out
