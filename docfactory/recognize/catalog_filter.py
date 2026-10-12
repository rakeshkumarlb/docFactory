"""The part of the entity graph a recognition call sees: the existing entities a window may refer to. Deterministic, no LLM.

Sending the whole graph would not fit a small context once it grows, so a window gets the entities whose name or an alias appears in its
text (matched as whole words, ignoring case, dashes and quotes), plus every entity of the types its rule-tag hints point to (a window under
'Environments' sees every environment, so 'Prod' can be matched to 'Production'), capped at MAX_ENTITIES.
"""
import re

from docfactory.extract.grounding import normalize
from docfactory.models.entity_record import EntityRecord

MAX_ENTITIES = 80


def mentioned(name: str, text: str) -> bool:
    """True when `name` appears in `text` as whole words, compared normalized."""
    needle = normalize(name)
    return bool(needle) and re.search(r"(?<![\w-])" + re.escape(needle) + r"(?![\w-])", normalize(text)) is not None


def catalog_for(window_text: str, entities: list[EntityRecord], hint_types: set[str]) -> list[EntityRecord]:
    """The existing entities a window may refer to: named in its text first, then those of the hinted types; at most MAX_ENTITIES."""
    named = [e for e in entities if any(mentioned(n, window_text) for n in [e.name, *e.aliases])]
    hinted = [e for e in entities if e.type in hint_types and e not in named]
    return (named + hinted)[:MAX_ENTITIES]


def catalog_text(entities: list[EntityRecord]) -> str:
    """The catalog as the prompt shows it: one '<entity id> | <type> | <name> | aka <aliases>' line per entity, or '(none yet)'."""
    if not entities:
        return "(none yet)"
    return "\n".join(f"{e.entity_id} | {e.type} | {e.name}" + (f" | aka {', '.join(e.aliases)}" if e.aliases else "") for e in entities)
