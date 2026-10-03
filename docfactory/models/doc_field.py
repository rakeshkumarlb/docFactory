from typing import Any

from pydantic import Field


RENDER_STYLES = {"list", "table", "numbered"}


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
    pattern: str | None = None,
    render_as: str = "list",
):
    """Declare a model field with its docFactory metadata. `default=...` means mandatory.

    `description` becomes the Pydantic field description. `question` (falling back to the
    description), `na_allowed`, `scored`, `binding` and `render_as` are stored in `json_schema_extra`.

    `render_as` is a presentation choice for a list field only. On a list of models: `"list"` (default)
    renders each item as a numbered detail list, `"table"` renders all items as one Markdown table.
    On a list of strings: `"list"` renders bullets, `"numbered"` renders an ordered list (for steps).
    It has no effect on scalar fields or on validation/completeness; the renderer decides what to do with it.
    """
    if render_as not in RENDER_STYLES:
        raise ValueError(f"render_as must be one of {sorted(RENDER_STYLES)}, got {render_as!r}")
    extra = {
        "question": question or description,
        "na_allowed": na_allowed,
        "scored": scored,
        "binding": binding,
        "render_as": render_as,
    }
    kwargs = {"description": description, "json_schema_extra": extra}
    if min_length is not None:
        kwargs["min_length"] = min_length
    if pattern is not None:
        kwargs["pattern"] = pattern
    if default_factory is not None:
        kwargs["default_factory"] = default_factory
    elif default is not ...:
        kwargs["default"] = default
    return Field(**kwargs)
