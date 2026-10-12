"""The entity types recognition may use. Derived from the fact registry (never hand-kept), plus a few graph-only types. Deterministic.

Three kinds of type:
- **item types**: the item model of every list-of-models field of a registered fact (Component -> Architecture.components). An entity of
  such a type becomes one item of that fact, filled by entity-centric extraction. The definition is the item model's docstring.
- **identifier types**: item types identified by a document identifier (their identity field is `id`, e.g. Requirement FR-12). Their rows are
  many and numbered, so the existing batch extraction handles them; recognition does not list them.
- **graph types**: kinds of thing the documents discuss that no template field holds yet (runbooks, decisions, risks, ...). Their entities
  are kept in the entity graph and linked, never lost; they reach documents only once a model exists for them.
A type that fits none of these is written `proposed:<PascalName>`; such entities are kept too and feed the type proposals.
A type applied from a proposal becomes an item type automatically, because it is a registered fact with a list of items.
"""
import re

from pydantic import BaseModel

from docfactory.bundle.fact_registry import FACT_SPECS
from docfactory.bundle.item_layout import split_fields
from docfactory.extract.model_shapes import identity_field

PROPOSED_PREFIX = "proposed:"
NOT_RECOGNIZED_FACTS = {"Note"}  # written by discovery from left-over chunks; never an entity type
GRAPH_TYPES = {
    "Runbook": "A step-by-step response to an operational event, usually tied to an alert or incident, e.g. 'RB-01 High API Error Rate'.",
    "Decision": "An architecture or design decision with its reason, e.g. 'ADR-002 Use OpenSearch for candidate retrieval'.",
    "Risk": "A risk of a risk register with its likelihood, impact or mitigation, e.g. 'RSK-03 Loss of data centre DC1'.",
    "Release": "A released version of the application with its changes, e.g. '1.3.0'.",
    "Team": "A team of people that owns, builds or runs parts of the application, e.g. 'Matching Team'.",
    "Role": "A job role with responsibilities, e.g. 'Release Manager' or 'On-Call Engineer'. A support contact (a role in the support or escalation chain) is a SupportContact instead.",
    "Tool": "A tool or product used to build, deploy, monitor or operate the application that is not one of its own components or data stores, e.g. 'Prometheus', 'GitLab CI', 'Terraform'.",
    "Infrastructure": "A piece of hosting infrastructure: a cluster, data centre, network zone or server group, e.g. 'jm-prod cluster', 'Data Centre DC1'. Not an environment: an environment is hosted on infrastructure.",
    "Organization": "An organisation outside the team: a ministry, a funder, a partner, a customer, e.g. 'Ministry of Labour'.",
    "Capability": "A business capability or feature area of the application as a whole, e.g. 'Resume Parsing' or 'Job Search and Filtering'. Not a component: a capability is what the application does, a component is a part that does it.",
    "UserGroup": "A class of users of the application, e.g. 'Job Seekers' or 'Employers'.",
}
_PASCAL = re.compile(r"[A-Z][A-Za-z0-9]+")


def item_types() -> dict[str, tuple[str, str, type[BaseModel]]]:
    """Item type name -> (fact entity, list field, item model) for every list-of-models field of a registered fact, in registry order."""
    found: dict[str, tuple[str, str, type[BaseModel]]] = {}
    for entity, spec in FACT_SPECS.items():
        if entity in NOT_RECOGNIZED_FACTS:
            continue
        for field, model in split_fields(spec["model"]).items():
            found.setdefault(model.__name__, (entity, field, model))
    return found


def identifier_types() -> set[str]:
    """The item types identified by a document identifier (identity field `id`), handled by batch extraction, not by recognition."""
    return {name for name, (_, _, model) in item_types().items() if identity_field(model) == "id"}


def entity_types() -> dict[str, str]:
    """Type name -> definition of every type recognition may use: item types (not identifier types) first, then graph types."""
    items = {name: " ".join((model.__doc__ or "").split()) for name, (_, _, model) in item_types().items() if name not in identifier_types()}
    return items | {name: text for name, text in GRAPH_TYPES.items() if name not in items}


def types_of_fact(entity: str) -> list[str]:
    """The recognizable item types a fact holds, e.g. Architecture -> [Component, DataStore, Integration]."""
    skip = identifier_types()
    return [name for name, (fact, _, _) in item_types().items() if fact == entity and name not in skip]


def is_proposed(type_name: str) -> bool:
    return type_name.startswith(PROPOSED_PREFIX)


def type_problem(type_name: str) -> str | None:
    """Why `type_name` cannot be used (None when it can): not a vocabulary type, an identifier type, or a badly written proposal."""
    if is_proposed(type_name):
        name = type_name[len(PROPOSED_PREFIX):]
        if not _PASCAL.fullmatch(name):
            return f"{type_name!r}: a proposed type is written 'proposed:<PascalName>', e.g. 'proposed:Certificate'"
        if name in entity_types() or name in identifier_types():
            return f"{type_name!r}: {name} is already a vocabulary type; use it without 'proposed:'"
        return None
    if type_name in identifier_types():
        return f"{type_name!r}: identified rows such as FR-12 are extracted by rules; do not list them"
    if type_name not in entity_types():
        return f"{type_name!r} is not a vocabulary type; use one of the listed types or 'proposed:<PascalName>'"
    return None


def vocabulary_text() -> str:
    """The vocabulary as the recognition prompt shows it: one '- <Type>: <definition>' line per type."""
    return "\n".join(f"- {name}: {text}" for name, text in entity_types().items())
