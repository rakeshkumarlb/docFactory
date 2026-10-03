"""Key pattern -> entity saver resolution: which saver owns a fact key. Every entity saver in docfactory/entitysaver/ is found here."""
import importlib
import pkgutil

from docfactory import documentsaver, entitysaver
from docfactory.base_saver import BaseSaver


def _saver_classes(package) -> list[type[BaseSaver]]:
    classes = []
    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package.__name__}.{module_info.name}")
        classes += [
            value for value in vars(module).values()
            if isinstance(value, type) and issubclass(value, BaseSaver) and value is not BaseSaver and value.__module__ == module.__name__
        ]
    return sorted(classes, key=lambda cls: cls.model.__name__)


def entity_saver_classes() -> list[type[BaseSaver]]:
    """Every entity saver class (one per module of docfactory/entitysaver/), ordered by the name of its model."""
    return _saver_classes(entitysaver)


def document_saver_classes() -> list[type[BaseSaver]]:
    """Every document body saver class (one per module of docfactory/documentsaver/documents/), ordered by the name of its model."""
    from docfactory.documentsaver import documents

    return _saver_classes(documents)


def _resolve(classes: list[type[BaseSaver]], key: str) -> BaseSaver | None:
    matches = [cls() for cls in classes if cls().accepts_key(key)]
    if len(matches) > 1:
        raise RuntimeError(f"key {key!r} matches more than one saver: {[type(m).__name__ for m in matches]}")
    return matches[0] if matches else None


def saver_for_key(key: str) -> BaseSaver | None:
    """The entity saver whose key patterns accept `key`, or None. Two matching savers is a configuration error (RuntimeError)."""
    return _resolve(entity_saver_classes(), key)


def document_saver_for_key(key: str) -> BaseSaver | None:
    """The document body saver whose key patterns accept `key` (e.g. ReadmeForge.Outputs.SMTD), or None."""
    return _resolve(document_saver_classes(), key)


def ordered_value(key: str, value_json: str) -> str:
    """The stored JSON of a fact with its fields in model order (canonical JSON is sorted); unchanged when no saver owns the key."""
    saver = saver_for_key(key)
    if saver is None:
        return value_json
    return saver.model.model_validate_json(value_json).model_dump_json()
