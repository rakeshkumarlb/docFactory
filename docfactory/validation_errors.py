"""Pydantic validation errors as SaveErrors carrying each field's description and question (feedback a caller can act on)."""
import inspect
import json
from typing import get_args

from pydantic import BaseModel, ValidationError

from docfactory.models.save_error import SaveError

INPUT_SHOULD_BE = "Input should be "


def json_text(value) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return repr(value)


def _model_classes(annotation) -> list:
    """Every model class inside an annotation (through Optional, unions and lists)."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [annotation]
    found = []
    for argument in get_args(annotation):
        found += _model_classes(argument)
    return found


def _walk(model, loc):
    """Follow an error location through the model fields: (last matched field or None, model classes reached)."""
    candidates, field = [model], None
    for part in loc:
        if not isinstance(part, str):
            continue  # list index
        for cls in candidates:
            if part in cls.model_fields:
                field = cls.model_fields[part]
                candidates = _model_classes(field.annotation)
                break
        # a part that is no field name is a union member tag: ignore it
    return field, candidates


def _expected(error: dict) -> str | None:
    context = error.get("ctx") or {}
    if "expected" in context:
        return str(context["expected"])
    message = error["msg"]
    if error["type"] == "missing":
        return "a value for this field"
    if error["type"] == "extra_forbidden":
        return "no such field; remove it"
    if message.startswith(INPUT_SHOULD_BE):
        return message[len(INPUT_SHOULD_BE):]
    return None


def validation_errors(model, error: ValidationError) -> list[SaveError]:
    """Pydantic errors as SaveErrors carrying each field's description and question (feedback a caller can act on)."""
    out = []
    for item in error.errors():
        loc = item["loc"]
        description = question = None
        if item["type"] == "extra_forbidden":
            _, candidates = _walk(model, loc[:-1])
            owner = candidates[0] if candidates else model
            description = inspect.getdoc(owner)
            question = f"'{loc[-1]}' is not a field of {owner.__name__}. Which of its fields ({', '.join(owner.model_fields)}) does this information belong to?"
        else:
            field, _ = _walk(model, loc)
            if field is not None:
                description = field.description
                extra = field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}
                question = extra.get("question") or field.description
        out.append(
            SaveError(
                path=".".join(str(part) for part in loc) or "payload",
                message=item["msg"],
                error_type=item["type"],
                received=None if item["type"] == "missing" else json_text(item.get("input")),
                expected=_expected(item),
                field_description=description,
                question=question,
            )
        )
    return out
