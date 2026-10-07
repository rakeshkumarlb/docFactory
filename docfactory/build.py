"""Builds a document body object from an application's stored facts, deterministically.

`build_document` walks a document model's own fields, using each field's `binding` metadata
(set by `doc_field`) to find the fact and source field that supply it. It invents nothing: a
field is copied over only when its source fact answers it (see `completeness.py` for the same
"answered" rule); otherwise the field is left at its own default and recorded in the returned
`missing` list, generated from the model's metadata rather than written by hand.
"""
import json
from typing import get_args

from docfactory import db
from docfactory.documentmodels.shared.missing_info import MissingInfo
from docfactory.entitymodels.facts.application_overview import ApplicationOverview
from docfactory.entitymodels.facts.architecture import Architecture
from docfactory.entitymodels.facts.backup_recovery import BackupRecovery
from docfactory.entitymodels.facts.deployment import Deployment
from docfactory.entitymodels.facts.environments import Environments
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.entitymodels.facts.known_errors import KnownErrors
from docfactory.entitymodels.facts.kpis import Kpis
from docfactory.entitymodels.facts.monitoring import Monitoring
from docfactory.entitymodels.facts.non_functional_requirements import NonFunctionalRequirements
from docfactory.entitymodels.facts.slo import Slo
from docfactory.entitymodels.facts.sop import Sop
from docfactory.entitymodels.facts.support import Support
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.not_applicable import NotApplicable

# Which fact name a "<FactName>.<field>" binding loads, and whether it is Shared (AppID NULL) or
# application-specific. A registry that discovers this from the entity savers themselves is Phase 2.
FACT_SPECS = {
    "ApplicationOverview": {"model": ApplicationOverview, "shared": False},
    "Kpis": {"model": Kpis, "shared": True},
    "Architecture": {"model": Architecture, "shared": False},
    "BackupRecovery": {"model": BackupRecovery, "shared": False},
    "Deployment": {"model": Deployment, "shared": False},
    "Environments": {"model": Environments, "shared": False},
    "FunctionalRequirements": {"model": FunctionalRequirements, "shared": False},
    "KnownErrors": {"model": KnownErrors, "shared": False},
    "Monitoring": {"model": Monitoring, "shared": False},
    "NonFunctionalRequirements": {"model": NonFunctionalRequirements, "shared": False},
    "Slo": {"model": Slo, "shared": True},
    "Sop": {"model": Sop, "shared": False},
    "Support": {"model": Support, "shared": False},
}


class BuildError(Exception):
    """Raised when a document model is wired wrongly: a binding names an unknown fact, or a field has no fact binding."""


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
    return model_cls.model_validate(values)  # section fields all have defaults: an absent fact is a gap, never an invalid section


def build_document(document_model: type[DocFactoryModel], app_id: str) -> tuple[DocFactoryModel, list[MissingInfo]]:
    """Build a `document_model` body object from `app_id`'s facts and the shared facts.

    Returns (instance, missing): `missing` lists every field build_document could not fill, generated
    from the model's own metadata. An absent or incomplete fact never stops the build: its fields keep
    their defaults and are listed in `missing`. Raises BuildError only for a wrongly wired model.
    """
    missing: list[MissingInfo] = []
    instance = _build_model(document_model, app_id, {}, "", missing)
    return instance, missing
