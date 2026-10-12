"""The ingestion ontology's tagging signals: one validated EntitySignals entry per entity, read from signals.json (the file people edit)."""
import json
from pathlib import Path

from pydantic import TypeAdapter

from docfactory.bundle.fact_registry import taggable_entity_names
from docfactory.models.entity_signals import EntitySignals

SIGNALS_FILE = Path(__file__).with_name("signals.json")


def entity_names() -> list[str]:
    """The closed list of entities a chunk can be tagged with: the taggable facts of the fact registry (not Note), ordered by name."""
    return taggable_entity_names()


def load_signals(path: Path = SIGNALS_FILE) -> list[EntitySignals]:
    """The validated signals, one per entity, in the order of `entity_names()`.

    Raises ValueError when an entity has no entry, an entry names an unknown entity, or an entity appears twice.
    """
    entries = TypeAdapter(list[EntitySignals]).validate_python(json.loads(path.read_text(encoding="utf-8")))
    names = entity_names()
    by_entity: dict[str, EntitySignals] = {}
    for entry in entries:
        if entry.entity not in names:
            raise ValueError(f"signals name an unknown entity {entry.entity!r}; entities are {names}")
        if entry.entity in by_entity:
            raise ValueError(f"entity {entry.entity!r} has more than one signals entry")
        by_entity[entry.entity] = entry
    missing = [name for name in names if name not in by_entity]
    if missing:
        raise ValueError(f"entities without signals: {missing}; add them to {path.name}")
    return [by_entity[name] for name in names]
