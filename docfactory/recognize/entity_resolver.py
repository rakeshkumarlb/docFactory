import re

from docfactory.extract.grounding import normalize
from docfactory.models.entity_record import EntityRecord

_NON_WORD = re.compile(r"[^a-z0-9]+")


def name_key(name: str) -> str:
    """A name as compared for identity: normalized, punctuation dropped, a leading 'the' and a trailing plural 's' ignored
    ('The Matching-Engine' == 'matching engine'; 'Environments' == 'environment')."""
    key = _NON_WORD.sub(" ", normalize(name)).strip()
    key = re.sub(r"^the ", "", key)
    return re.sub(r"(?<=[a-z]{3})s$", "", key)


class EntityResolver:
    """Finds the entity a name refers to: by entity id, or by name or alias compared with `name_key`, optionally within one type.
    Deterministic; the first entity registered under a key keeps it (later look-alikes do not steal it)."""

    def __init__(self, records: list[EntityRecord] | None = None) -> None:
        self.by_id: dict[str, EntityRecord] = {}
        self._by_key: dict[tuple[str, str], str] = {}  # (type, name key) -> entity id
        self._any: dict[str, str] = {}  # name key -> entity id, any type
        for record in records or []:
            self.register(record)

    def register(self, record: EntityRecord) -> None:
        """Index (or re-index) an entity under its id, name and aliases."""
        self.by_id[record.entity_id] = record
        for name in [record.name, *record.aliases]:
            key = name_key(name)
            if key:
                self._by_key.setdefault((record.type, key), record.entity_id)
                self._any.setdefault(key, record.entity_id)

    def find(self, name: str, type_name: str | None = None) -> EntityRecord | None:
        """The entity `name` refers to (an id, a name or an alias), within `type_name` when given; None when unknown."""
        if name in self.by_id:
            return self.by_id[name]
        key = name_key(name)
        entity_id = self._by_key.get((type_name, key)) if type_name is not None else self._any.get(key)
        return self.by_id.get(entity_id) if entity_id else None
