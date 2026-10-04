"""What shape an entity field has, read from its annotation (Phase 3 merging, grounding and missing-info checks). Deterministic.

Values are handled as JSON (as stored in KnowledgeFacts), so these helpers tell code which model a nested dict or a list item
follows, and which field of a list item identifies it.
"""
from enum import Enum
from typing import get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from docfactory.models.not_applicable import NotApplicable


def _members(annotation) -> list:
    args = get_args(annotation)
    return [a for arg in args for a in _members(arg)] if args and get_origin(annotation) is not list else [annotation]


def item_model(annotation) -> type[BaseModel] | None:
    """The model of the items when the field is a list of models (e.g. list[Requirement] -> Requirement), else None."""
    for member in _members(annotation):
        if get_origin(member) is list:
            (item,) = get_args(member)
            if isinstance(item, type) and issubclass(item, BaseModel):
                return item
    return None


def nested_model(annotation) -> type[BaseModel] | None:
    """The model when the field holds one nested model (not NotApplicable), else None."""
    for member in _members(annotation):
        if isinstance(member, type) and issubclass(member, BaseModel) and member is not NotApplicable:
            return member
    return None


def is_enum(annotation) -> bool:
    """True when the field's value is an enum member (a closed choice, never copied from the text)."""
    return any(isinstance(m, type) and issubclass(m, Enum) for m in _members(annotation))


def identity_field(model: type[BaseModel]) -> str:
    """The field that identifies an item of a list: its first mandatory field (Requirement.id, Component.name, SupportContact.role)."""
    for name, field in model.model_fields.items():
        if field.is_required():
            return name
    raise ValueError(f"{model.__name__} has no mandatory field to identify its items")


def question_of(field: FieldInfo) -> str:
    extra = field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}
    return extra.get("question") or field.description or ""
