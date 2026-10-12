"""The part of the entity graph a recognition call sees: the existing entities a window may refer to. Deterministic, no LLM.

A window sees, in this order: the entities whose name or an alias appears in its text (matched as whole words, ignoring case, dashes and
quotes), every entity of the types its rule-tag hints point to (a window under 'Environments' sees every environment, so 'Prod' can be
matched to 'Production'), then the rest of the graph, item types before graph-only types, so a name the window writes differently
('Matching Engine' for 'AI-Driven Matching Engine') can still be matched. At most MAX_ENTITIES (env DOCFACTORY_CATALOG_MAX, default 200,
sized for a 64k-token context); the order decides what is cut when the graph is larger.
"""
import os
import re

from docfactory.extract.grounding import normalize
from docfactory.models.entity_record import EntityRecord
from docfactory.recognize.type_vocabulary import type_rank

MAX_ENTITIES_ENV = "DOCFACTORY_CATALOG_MAX"
DEFAULT_MAX_ENTITIES = 200


def max_entities() -> int:
    """The catalog cap: env DOCFACTORY_CATALOG_MAX, else 200."""
    return int(os.environ.get(MAX_ENTITIES_ENV) or DEFAULT_MAX_ENTITIES)


def mentioned(name: str, text: str) -> bool:
    """True when `name` appears in `text` as whole words, compared normalized."""
    needle = normalize(name)
    return bool(needle) and re.search(r"(?<![\w-])" + re.escape(needle) + r"(?![\w-])", normalize(text)) is not None


def catalog_for(window_text: str, entities: list[EntityRecord], hint_types: set[str], cap: int | None = None) -> list[EntityRecord]:
    """The existing entities a window may refer to, most relevant first (see the module docstring); at most `cap` (default `max_entities()`)."""
    named = [e for e in entities if any(mentioned(n, window_text) for n in [e.name, *e.aliases])]
    hinted = [e for e in entities if e.type in hint_types and e not in named]
    rest = sorted((e for e in entities if e not in named and e not in hinted), key=lambda e: (-type_rank(e.type), e.entity_id))
    return (named + hinted + rest)[:cap or max_entities()]


def catalog_text(entities: list[EntityRecord]) -> str:
    """The catalog as the prompt shows it: one '<entity id> | <type> | <name> | aka <aliases>' line per entity, or '(none yet)'."""
    if not entities:
        return "(none yet)"
    return "\n".join(f"{e.entity_id} | {e.type} | {e.name}" + (f" | aka {', '.join(e.aliases)}" if e.aliases else "") for e in entities)
