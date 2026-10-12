"""Where the items of a fact's lists are stored: one concept file per item under the fact's own folder. Deterministic, writes nothing.

The fact `Acme.FunctionalRequirements` is the parent concept `Acme/FunctionalRequirements.md`; each item of its `requirements` list is
`Acme/FunctionalRequirements/requirements/<slug>.md`. A list of models (a field typed list[Model]) is split into items; lists of plain text,
nested single models and scalar fields stay in the parent. Item models are not registered facts: the split follows the fact model.
"""
import re
from enum import Enum

from pydantic import BaseModel

from docfactory.bundle.paths import SUFFIX, fact_relpath, is_safe_segment
from docfactory.extract.model_shapes import identity_field, item_model

MAX_SLUG = 80
_BAD = re.compile(r'[\x00-\x1f/\:*?"<>|\s]+')


def split_fields(model: type[BaseModel]) -> dict[str, type[BaseModel]]:
    """The fields of a fact model that are split into item files (field name -> item model), in model field order."""
    return {name: item for name, field in model.model_fields.items() if (item := item_model(field.annotation)) is not None}


def item_id_of(item: BaseModel) -> str:
    """The identifier of an item: the value of its identity field (its first mandatory field), as text."""
    value = getattr(item, identity_field(type(item)))
    return str(value.value if isinstance(value, Enum) else value)


def _slug(text: str) -> str:
    cleaned = _BAD.sub("-", text).strip("-. ")[:MAX_SLUG].strip("-. ") or "item"
    return cleaned if is_safe_segment(cleaned) else f"_{cleaned}"


def item_slugs(ids: list[str]) -> list[str]:
    """One file-name stem per id, in order: unsafe characters become '-', and a repeated stem (compared ignoring case) gets '~2', '~3', ..."""
    seen: dict[str, int] = {}
    stems = []
    for item_id in ids:
        base = _slug(item_id)
        count = seen.get(base.lower(), 0) + 1
        seen[base.lower()] = count
        stems.append(base if count == 1 else f"{base}~{count}")
    return stems


def entity_dir(key: str) -> str:
    """The bundle-relative folder of a fact's items, forward slashes, no trailing slash: 'Acme.FunctionalRequirements' -> 'Acme/FunctionalRequirements'."""
    return fact_relpath(key).removesuffix(SUFFIX)


def item_relpath(key: str, field: str, stem: str) -> str:
    """The bundle-relative path of an item's concept file: ('Acme.FunctionalRequirements', 'requirements', 'FR-01') -> 'Acme/FunctionalRequirements/requirements/FR-01.md'."""
    return f"{entity_dir(key)}/{field}/{stem}{SUFFIX}"
