"""Key pattern -> entity saver resolution: which saver owns a fact key. Every entity saver in docfactory/entitysaver/ is found here."""
import importlib
import pkgutil

from docfactory import entitysaver
from docfactory.base_saver import BaseSaver


def entity_saver_classes() -> list[type[BaseSaver]]:
    """Every entity saver class (one per module of docfactory/entitysaver/), ordered by the name of its model."""
    classes = []
    for module_info in pkgutil.iter_modules(entitysaver.__path__):
        module = importlib.import_module(f"{entitysaver.__name__}.{module_info.name}")
        classes += [
            value for value in vars(module).values()
            if isinstance(value, type) and issubclass(value, BaseSaver) and value is not BaseSaver and value.__module__ == module.__name__
        ]
    return sorted(classes, key=lambda cls: cls.model.__name__)


def saver_for_key(key: str) -> BaseSaver | None:
    """The saver whose key patterns accept `key`, or None. Two matching savers is a configuration error (RuntimeError)."""
    matches = [cls() for cls in entity_saver_classes() if cls().accepts_key(key)]
    if len(matches) > 1:
        raise RuntimeError(f"key {key!r} matches more than one saver: {[type(m).__name__ for m in matches]}")
    return matches[0] if matches else None


def ordered_value(key: str, value_json: str) -> str:
    """The stored JSON of a fact with its fields in model order (canonical JSON is sorted); unchanged when no saver owns the key."""
    saver = saver_for_key(key)
    if saver is None:
        return value_json
    return saver.model.model_validate_json(value_json).model_dump_json()
