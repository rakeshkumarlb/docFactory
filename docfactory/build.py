"""Builds a document body object from an application's stored facts, deterministically.

`build_document` walks a document model's own fields, using each field's `binding` metadata
(set by `doc_field`) to find the fact and source field that supply it. It invents nothing: a
field is copied over only when its source fact answers it (see `completeness.py` for the same
"answered" rule); otherwise the field is left at its own default and recorded in the returned
`missing` list, generated from the model's metadata rather than written by hand.
"""
import json
from typing import get_args

from pydantic import ValidationError

from docfactory import db
from docfactory.documentmodels.shared.missing_info import MissingInfo
from docfactory.entitymodels.application_overview import ApplicationOverview
from docfactory.entitymodels.kpis import Kpis
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.not_applicable import NotApplicable

# Which fact name a "<FactName>.<field>" binding loads, and whether it is Shared (AppID NULL) or
# application-specific. A registry that discovers this from the entity savers themselves is Phase 2.
FACT_SPECS = {
    "ApplicationOverview": {"model": ApplicationOverview, "shared": False},
    "Kpis": {"model": Kpis, "shared": True},
}


class BuildError(Exception):
    """Raised when build_document cannot fill a mandatory document field because its source fact is missing."""


def _extra(field) -> dict:
    return field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}


def _nested_model_class(annotation):
    """The single DocFactoryModel subclass inside an annotation (a plain type or wrapped in Optional/Union)."""
    if isinstance(annotation, type) and issubclass(annotation, DocFactoryModel):
        return annotation
    for argument in get_args(annotation):
        found = _nested_model_class(argument)
        if found is not None:
            return found
    return None


def _load_fact(app_id: str, fact_name: str, cache: dict):
    """The stored fact object for `fact_name`, or None when no row exists. Cached per build_document call."""
    if fact_name not in cache:
        spec = FACT_SPECS.get(fact_name)
        if spec is None:
            raise BuildError(f"build_document does not know how to load fact {fact_name!r}; add it to FACT_SPECS")
        key = f"Shared.{fact_name}" if spec["shared"] else f"{app_id}.{fact_name}"
        row = db.get_row("KnowledgeFacts", key)
        cache[fact_name] = spec["model"].model_validate(json.loads(row["Value"])) if row else None
    return cache[fact_name]


def _is_answered(source_field, value) -> bool:
    """A source field is answered when it is mandatory (guaranteed by validation), holds a NotApplicable, or differs from its own default."""
    if isinstance(value, NotApplicable) or source_field.is_required():
        return True
    return value != source_field.get_default(call_default_factory=True)


def _build_model(model_cls, app_id: str, cache: dict, prefix: str, missing: list):
    values = {}
    for name, field in model_cls.model_fields.items():
        extra = _extra(field)
        binding = extra.get("binding")
        dotted = f"{prefix}.{name}" if prefix else name
        if binding == "composed":
            values[name] = _build_model(_nested_model_class(field.annotation), app_id, cache, dotted, missing)
            continue
        if not binding or binding == "caller":
            raise BuildError(
                f"{model_cls.__name__}.{name} has binding {binding!r}; build_document only builds fields bound "
                "to a fact ('FactName.field') or 'composed' sections, never caller-supplied ones"
            )
        fact_name, _, source_name = binding.partition(".")
        fact = _load_fact(app_id, fact_name, cache)
        source_field = type(fact).model_fields.get(source_name) if fact is not None else None
        if fact is not None and source_field is not None and _is_answered(source_field, getattr(fact, source_name)):
            values[name] = getattr(fact, source_name)
        else:
            missing.append(MissingInfo(field=dotted, question=extra.get("question") or field.description, expected_source=binding))
    try:
        return model_cls.model_validate(values)
    except ValidationError as error:
        unresolved = ", ".join(item.field for item in missing if item.field.startswith(prefix)) or "unknown field(s)"
        raise BuildError(f"Cannot build {model_cls.__name__}: mandatory field(s) have no source fact yet: {unresolved}") from error


def build_document(document_model: type[DocFactoryModel], app_id: str) -> tuple[DocFactoryModel, list[MissingInfo]]:
    """Build a `document_model` body object from `app_id`'s facts and the shared facts.

    Returns (instance, missing): `missing` lists every field build_document could not fill, generated
    from the model's own metadata. Raises BuildError, naming the unresolved fields, when a mandatory
    field has no source fact at all rather than inventing a value to satisfy it.
    """
    missing: list[MissingInfo] = []
    instance = _build_model(document_model, app_id, {}, "", missing)
    return instance, missing
