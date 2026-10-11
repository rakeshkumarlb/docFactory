"""Renders a document's stored parts (the state files) to Markdown: document control, revision history, then the body.

Document control, revision history and the field layout come from render.py; only the body differs: each stored value is validated
again against the type of the entity field it was copied from, and a missing field is shown as that field's default.
"""
import json
from typing import get_origin

from pydantic import TypeAdapter
from pydantic_core import PydanticUndefined

from docfactory.generation.document_parts import BODY, CONTROL, HISTORY, NEEDS, PART_MODELS, part_key
from docfactory.generation.document_state_store import DocumentStateStore
from docfactory.generation.bindings import source_field
from docfactory.documentmodels.document_body import DocumentBody
from docfactory.render import RenderError, field_lines, needs_markdown, render_document_control, render_revision_history


def _load(app_id: str, doc_type: str, part: str):
    value = DocumentStateStore().model(app_id, doc_type, part)
    if value is None:
        raise RenderError(f"Cannot render: no stored {part} for {part_key(app_id, doc_type, part)!r} ({PART_MODELS[part].__name__} is missing)")
    return value


def _value_of(field):
    source = source_field(field.binding)
    if field.status != "answered":
        default = source.get_default(call_default_factory=True)
        if default is not PydanticUndefined:
            return default
        return [] if get_origin(source.annotation) is list else ""  # a mandatory entity field whose fact is absent
    return TypeAdapter(source.annotation).validate_python(json.loads(field.value))


def _render_body(body: DocumentBody) -> str:
    lines = []
    for section in body.sections:
        lines += [f"## {section.title}", ""]
        for field in section.fields:
            lines += field_lines(field.label, _value_of(field), field.render_as, heading_level=3)
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def render_document_markdown(app_id: str, doc_type: str) -> str:
    """The full Markdown of `app_id`'s `doc_type` document: document control, revision history, then body.

    Reads the three stored parts of the document. Raises RenderError, naming the missing key, when one is not there.
    """
    control = _load(app_id, doc_type, CONTROL)
    history = _load(app_id, doc_type, HISTORY)
    body = _load(app_id, doc_type, BODY)
    return "\n\n".join([render_document_control(control), render_revision_history(history), _render_body(body)]) + "\n"


def render_document_needs(app_id: str, doc_type: str) -> str | None:
    """The needs list of the document as Markdown, from its stored needs list; None when there is none or no gap."""
    info = DocumentStateStore().model(app_id, doc_type, NEEDS)
    return None if info is None else needs_markdown(app_id, doc_type, info)
