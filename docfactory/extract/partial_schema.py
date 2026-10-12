"""The partial form of an entity model, for one extraction batch (Phase 3). Deterministic, no LLM.

A batch sees only part of a document, so it may return only some of a fact's fields: in the partial model every top-level field is
optional (None = not stated in this batch). Everything below the top level keeps the entity's own types, so a list item still needs
its mandatory fields and a bad value is rejected with the field's description and question. The partial model is built on the fly
from the entity model (like a tool's argument model), never declared by hand, so it cannot drift from the entity.
Fields named in `exclude` are left out of the partial model: code fills them (an item's identity, its evidence) or another step does (list
fields whose items come from the entity graph), so a call may not state them.
"""
from copy import copy
from functools import cache

from pydantic import BaseModel, ValidationError, create_model

from docfactory.validation_errors import validation_errors
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.save_error import SaveError


@cache
def partial_model(entity_model: type[BaseModel], exclude: frozenset[str] = frozenset()) -> type[BaseModel]:
    """`entity_model` with every top-level field optional (default None), minus the fields in `exclude`; descriptions, questions and constraints kept."""
    fields = {}
    for name, field in entity_model.model_fields.items():
        if name in exclude:
            continue
        optional = copy(field)
        optional.default, optional.default_factory = None, None
        fields[name] = (field.annotation | None, optional)
    suffix = "Partial" if not exclude else "Part"
    return create_model(f"{entity_model.__name__}{suffix}", __base__=DocFactoryModel, __doc__=entity_model.__doc__, **fields)


def is_empty(value) -> bool:
    """A value that states nothing: absent, None, an empty string or an empty list."""
    return value is None or value == "" or value == []


def partial_values(entity_model: type[BaseModel], values: dict, exclude: frozenset[str] = frozenset()) -> tuple[dict | None, list[SaveError]]:
    """(the stated fields as JSON-compatible values, []) or (None, errors). Fields equal to the entity's default state nothing and are dropped;
    a field in `exclude` is an error (the call may not state it)."""
    try:
        validated = partial_model(entity_model, exclude).model_validate(values)
    except ValidationError as error:
        return None, validation_errors(entity_model, error)
    stated = {}
    for name, value in validated.model_dump(mode="json", exclude_defaults=True).items():  # item fields left at their default state nothing either
        field = entity_model.model_fields[name]
        default = None if field.is_required() else field.get_default(call_default_factory=True)
        if is_empty(value) or value == default:
            continue
        stated[name] = value
    return stated, []
