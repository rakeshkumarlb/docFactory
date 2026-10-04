"""Merge partial fact values into one (Phase 3). Pure functions, deterministic, no LLM.

Used twice: the batches of one file merge into that file's contribution, and the contributions of all files merge into the fact.
Sources are given in precedence order (first wins):
- a scalar (or NotApplicable) takes the first non-empty value; a different non-empty value elsewhere is reported as a conflict;
- a list of strings is the union in first-seen order, de-duplicated ignoring case and spacing;
- a list of models is the union of items by their identity field (Requirement.id, Component.name, ...); items with the same
  identity merge field by field with the same rules, so an older source fills what the newer one left empty.
"""
from pydantic import BaseModel

from docfactory.canonical import canonical_json
from docfactory.extract.grounding import normal_identity, normalize
from docfactory.extract.model_shapes import identity_field, item_model
from docfactory.extract.partial_schema import is_empty

SHOWN_CHARS = 80

Source = tuple[str, dict]  # (label of the source, e.g. a DocStore path or 'chunk 17', its partial value)


def _shown(value) -> str:
    text = value if isinstance(value, str) else canonical_json(value)
    return repr(text if len(text) <= SHOWN_CHARS else text[:SHOWN_CHARS] + "...")


def _same(a, b) -> bool:
    if isinstance(a, str) and isinstance(b, str):
        return normalize(a) == normalize(b)
    return canonical_json(a) == canonical_json(b)


def _union_strings(values: list[tuple[str, list]]) -> list:
    seen, out = set(), []
    for _, items in values:
        for item in items:
            mark = normalize(item) if isinstance(item, str) else canonical_json(item)
            if mark not in seen:
                seen.add(mark)
                out.append(item)
    return out


def _merge_items(model: type[BaseModel], values: list[tuple[str, list]], path: str) -> tuple[list, list[str]]:
    identity = identity_field(model)
    groups: dict[str, list[Source]] = {}
    for label, items in values:
        for item in items:
            groups.setdefault(normal_identity(str(item.get(identity, ""))), []).append((label, item))
    merged, conflicts = [], []
    for group in groups.values():
        if len(group) == 1:
            merged.append(group[0][1])
            continue
        item, item_conflicts = _merge(model, group, f"{path}[{group[0][1].get(identity)}].", identity)
        merged.append(item)
        conflicts += item_conflicts
    return merged, conflicts


def _merge(model: type[BaseModel], sources: list[Source], path: str, identity: str | None = None) -> tuple[dict, list[str]]:
    out: dict = {}
    conflicts: list[str] = []
    for name, field in model.model_fields.items():
        values = [(label, data[name]) for label, data in sources if name in data and not is_empty(data[name])]
        if not values:
            continue
        items = item_model(field.annotation)
        if all(isinstance(value, list) for _, value in values):
            if items is not None:
                out[name], item_conflicts = _merge_items(items, values, f"{path}{name}")
                conflicts += item_conflicts
            else:
                out[name] = _union_strings(values)
            continue
        (kept_label, kept), *others = values
        out[name] = kept
        conflicts += [f"{path}{name}: kept {_shown(kept)} from {kept_label}; {label} says {_shown(value)}"
                      for label, value in others if not _same(kept, value) and name != identity]  # the identity matched already
    return out, conflicts


def merge_partials(model: type[BaseModel], sources: list[Source]) -> tuple[dict, list[str]]:
    """(the merged value, conflicts) of partial values of `model`, given in precedence order (first wins)."""
    return _merge(model, sources, "")
