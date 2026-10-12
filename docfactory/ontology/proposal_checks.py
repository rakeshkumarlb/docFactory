"""Checks of a proposed new entity type before it is stored (OKF redesign step 5). Deterministic, no LLM, writes nothing.

A proposal must name something the ontology does not already have (not an existing entity or item type, not nearly the same name), describe
its fields for an LLM like every model does, and bring tagging signals that do not already signal another entity. Every problem is a sentence
the proposing call can act on.
"""
import difflib
import re
from pathlib import Path

from docfactory.bundle.fact_registry import FACT_SPECS
from docfactory.models.proposal_field import ProposalField
from docfactory.models.proposal_field_type import ProposalFieldType
from docfactory.models.type_proposal import TypeProposal
from docfactory.ontology.signals import load_signals
from docfactory.project_root import PROJECT_ROOT

SIMILARITY = 0.85
MAX_FIELDS = 12
SNAKE = re.compile(r"[a-z][a-z0-9_]*")
ITEMS_DIR = PROJECT_ROOT / "docfactory" / "entitymodels" / "items"


def snake(name: str) -> str:
    """PascalCase to snake_case: 'RiskItem' -> 'risk_item'."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _plain(name: str) -> str:
    return re.sub(r"s$", "", name.lower())


def similar_to(name: str, known: list[str]) -> str | None:
    """The known name that `name` equals or nearly equals (ignoring case and a plural s), else None."""
    for other in known:
        if _plain(name) == _plain(other) or difflib.SequenceMatcher(None, _plain(name), _plain(other)).ratio() >= SIMILARITY:
            return other
    return None


def known_item_names() -> list[str]:
    """The class names of the item types and enums that exist (from the file names of entitymodels/items)."""
    return ["".join(part.capitalize() for part in path.stem.split("_")) for path in sorted(ITEMS_DIR.glob("*.py")) if path.stem != "__init__"]


def _field_errors(label: str, fields: list[ProposalField]) -> list[str]:
    errors = []
    names = [f.name for f in fields]
    errors += [f"{label}: the field name {n!r} is used twice" for n in sorted({n for n in names if names.count(n) > 1})]
    for field in fields:
        if "e.g." not in field.description:
            errors.append(f"{label}.{field.name}: the description needs an example introduced by 'e.g.'")
    return errors


def proposal_errors(proposal: TypeProposal, asked: set[int]) -> list[str]:
    """What is wrong with `proposal`, as sentences the proposing call can act on; empty when it can be stored."""
    errors = []
    near = similar_to(proposal.entity, list(FACT_SPECS))
    if near:
        errors.append(f"{proposal.entity!r} is the same as, or nearly the same as, the existing entity {near!r}: use that entity, or choose a clearly different kind of knowledge")
    errors += _field_errors(proposal.entity, proposal.fields)
    if not any(f.type == ProposalFieldType.TEXT for f in proposal.fields):
        errors.append(f"{proposal.entity}: at least one of its own fields must be of kind 'str' (for example a 'summary')")
    has_items = any((proposal.list_name, proposal.item_entity, proposal.item_doc, proposal.item_fields))
    if has_items:
        if not (proposal.list_name and proposal.item_entity and proposal.item_doc and proposal.item_fields):
            errors.append("an entity with items needs all of list_name, item_entity, item_doc and item_fields")
        else:
            if not SNAKE.fullmatch(proposal.list_name):
                errors.append(f"list_name {proposal.list_name!r} must be snake_case")
            if not re.fullmatch(r"[A-Z][A-Za-z0-9]+", proposal.item_entity):
                errors.append(f"item_entity {proposal.item_entity!r} must be PascalCase")
            elif similar_to(proposal.item_entity, known_item_names() + list(FACT_SPECS) + [proposal.entity]):
                errors.append(f"the item type {proposal.item_entity!r} is the same as, or nearly the same as, an existing type: choose another name or reuse that type")
            if proposal.list_name in {f.name for f in proposal.fields}:
                errors.append(f"list_name {proposal.list_name!r} is also a field of the entity")
            if proposal.item_fields[0].type != ProposalFieldType.TEXT:
                errors.append("the first item field identifies the item and must be of kind 'str'")
            errors += _field_errors(proposal.item_entity, proposal.item_fields)
    if len(proposal.fields) + len(proposal.item_fields) > MAX_FIELDS:
        errors.append(f"too many fields ({len(proposal.fields) + len(proposal.item_fields)}); keep at most {MAX_FIELDS} and only what the documents state")
    errors += [f"the heading term {t!r} must be lower case" for t in proposal.heading_terms + proposal.keywords if t != t.lower()]
    for pattern in proposal.id_patterns:
        try:
            re.compile(pattern)
        except re.error as error:
            errors.append(f"id_patterns entry {pattern!r} is not a valid regular expression: {error}")
    taken = {term: entry.entity for entry in load_signals() for term in entry.heading_terms}
    errors += [f"the heading term {t!r} already signals {taken[t]}: use terms that are specific to the new entity" for t in proposal.heading_terms if t in taken]
    unknown = sorted(set(proposal.sample_chunks) - asked)
    if unknown:
        errors.append(f"sample_chunks {unknown} were not given to you; use only {sorted(asked)}")
    return errors
