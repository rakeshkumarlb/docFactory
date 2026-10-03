import inspect
import json
import re
from typing import Generic, TypeVar, get_args

from pydantic import BaseModel, ValidationError

from docfactory import db
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.completeness import completeness
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.save_action import SaveAction
from docfactory.models.save_error import SaveError
from docfactory.models.save_result import SaveResult

M = TypeVar("M", bound=DocFactoryModel)

SHARED = "Shared"
PLACEHOLDER = re.compile(r"\{(app|component|doctype)\}")
INPUT_SHOULD_BE = "Input should be "
KEY_DESCRIPTION = "The unique key of the object: <Scope>.<Name>, where Scope is an application name or Shared."


def _pattern_matches(pattern: str, key: str) -> bool:
    """Whole-segment match. `{app}`, `{component}`, `{doctype}` stand for one non-empty segment; `Shared` is not an `{app}`."""
    segments, parts = pattern.split("."), key.split(".")
    if len(segments) != len(parts):
        return False
    for segment, part in zip(segments, parts):
        if PLACEHOLDER.fullmatch(segment):
            if not part or (segment == "{app}" and part == SHARED):
                return False
        elif segment != part:
            return False
    return True


def _app_id_of(key: str) -> str | None:
    first = key.split(".")[0]
    return None if first == SHARED else first


def _text(value) -> str:
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


def _validation_errors(model, error: ValidationError) -> list[SaveError]:
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
                received=None if item["type"] == "missing" else _text(item.get("input")),
                expected=_expected(item),
                field_description=description,
                question=question,
            )
        )
    return out


def _rejected(key, errors: list[SaveError]) -> SaveResult:
    return SaveResult(ok=False, key=str(key) or "(empty)", action=SaveAction.REJECTED, errors=errors)


class BaseSaver(Generic[M]):
    """Validates, hashes, versions, scores and stores one kind of object; concrete savers only declare `model` and `key_patterns`."""

    model: type[M]
    key_patterns: tuple[str, ...] = ()

    def _table(self) -> str:
        return "DocumentOutputs" if "documentsaver" in type(self).__module__ else "KnowledgeFacts"

    def _check_key(self, key, app_id) -> tuple[str | None, list[SaveError]]:
        """(AppID derived from the key, errors). Any error means the save is rejected."""
        patterns = ", ".join(self.key_patterns)
        if not isinstance(key, str) or not any(_pattern_matches(pattern, key) for pattern in self.key_patterns):
            return None, [
                SaveError(
                    path="key",
                    message=f"Key {key!r} does not match any key pattern of {type(self).__name__}",
                    error_type="key_pattern_mismatch",
                    received=_text(key),
                    expected=f"one of: {patterns}",
                    field_description=KEY_DESCRIPTION,
                    question=f"Which key should this {self.model.__name__} be saved under? Expected one of: {patterns}",
                )
            ]
        derived = _app_id_of(key)
        if app_id is not None and app_id != derived:
            return None, [
                SaveError(
                    path="app_id",
                    message=f"AppID {app_id!r} does not match the key {key!r}, whose AppID is {derived!r}",
                    error_type="app_id_mismatch",
                    received=_text(app_id),
                    expected=_text(derived),
                    field_description=KEY_DESCRIPTION,
                    question="Which application does this key belong to? The AppID must equal the key's first segment (none for Shared).",
                )
            ]
        return derived, []

    def save(self, key: str, payload, app_id: str | None = None) -> SaveResult:
        """Save the whole object under `key`. Never raises for bad input: a rejection is returned, nothing is written."""
        derived_app_id, key_errors = self._check_key(key, app_id)
        if key_errors:
            return _rejected(key, key_errors)
        try:
            instance = self.model.model_validate(payload)
        except ValidationError as error:
            return _rejected(key, _validation_errors(self.model, error))

        value = canonical_json(instance.model_dump(mode="json"))
        hashcode = sha256_hex(value)
        table = self._table()
        existing = db.get_row(table, key)
        if existing is not None and existing["Hashcode"] == hashcode:
            return SaveResult(
                ok=True,
                key=key,
                action=SaveAction.UNCHANGED,
                version=existing["Version"],
                hashcode=existing["Hashcode"],
                completeness=existing["Completeness"],
            )
        action, version = (SaveAction.CREATED, 1) if existing is None else (SaveAction.UPDATED, existing["Version"] + 1)
        score = completeness(instance)
        db.write_row(table, key, value, hashcode, derived_app_id, score, version)
        return SaveResult(ok=True, key=key, action=action, version=version, hashcode=hashcode, completeness=score)
