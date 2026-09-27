from typing import Any

from pydantic import Field


def doc_field(
    default: Any = ...,
    *,
    default_factory=None,
    description: str,
    question: str | None = None,
    na_allowed: bool = False,
    scored: bool = True,
    binding: str | None = None,
    min_length: int | None = None,
):
    """Declare a model field with its docFactory metadata. `default=...` means mandatory.

    `description` becomes the Pydantic field description. `question` (falling back to the
    description), `na_allowed`, `scored` and `binding` are stored in `json_schema_extra`.
    """
    extra = {
        "question": question or description,
        "na_allowed": na_allowed,
        "scored": scored,
        "binding": binding,
    }
    kwargs = {"description": description, "json_schema_extra": extra}
    if min_length is not None:
        kwargs["min_length"] = min_length
    if default_factory is not None:
        kwargs["default_factory"] = default_factory
    elif default is not ...:
        kwargs["default"] = default
    return Field(**kwargs)
