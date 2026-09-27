from pydantic import BaseModel
from pydantic.fields import FieldInfo

from docfactory.models.not_applicable import NotApplicable


def _is_scored(field: FieldInfo) -> bool:
    extra = field.json_schema_extra
    return not (isinstance(extra, dict) and extra.get("scored", True) is False)


def _model_counts(model: BaseModel) -> tuple[int, int]:
    """Counts of a present nested model. A model without any scored field counts as one answered field."""
    answered, total = field_counts(model)
    return (answered, total) if total else (1, 1)


def _present_counts(value) -> tuple[int, int]:
    """Counts of a value that is known to be answered (mandatory, or different from its default)."""
    if isinstance(value, BaseModel):
        return _model_counts(value)
    if isinstance(value, list) and any(isinstance(item, BaseModel) for item in value):
        answered = total = 0
        for item in value:
            if isinstance(item, BaseModel):
                item_answered, item_total = _model_counts(item)
                answered += item_answered
                total += item_total
            else:
                answered += 1
                total += 1
        return answered, total
    return 1, 1


def _field_counts(field: FieldInfo, value) -> tuple[int, int]:
    if isinstance(value, NotApplicable):
        return 1, 1
    if field.is_required():
        return _present_counts(value)  # a mandatory field is answered by definition
    if isinstance(value, list) and not value:
        return 0, 1  # an empty list is one unanswered field
    if value == field.get_default(call_default_factory=True):
        return 0, 1
    return _present_counts(value)


def field_counts(obj: BaseModel) -> tuple[int, int]:
    """(answered, total) leaf-field counts of a model object, recursive over nested models and list items.

    A field is answered when its value differs from its default or is a NotApplicable; mandatory fields
    are answered by definition; fields declared scored=False are left out of both counts.
    """
    answered = total = 0
    for name, field in type(obj).model_fields.items():
        if not _is_scored(field):
            continue
        field_answered, field_total = _field_counts(field, getattr(obj, name))
        answered += field_answered
        total += field_total
    return answered, total


def completeness(obj: BaseModel) -> float:
    """Completeness of a model object, 0 to 100: answered fields / total fields * 100.

    An object with no scored field at all has nothing left to answer and scores 100.
    """
    answered, total = field_counts(obj)
    return 100.0 if total == 0 else answered / total * 100
