"""Renders a document's stored rows (`DocumentOutputs`) to Markdown: document control, revision history, then the body.

Document control, revision history and the field layout come from render.py; only the body differs: each stored value is validated
again against the type of the entity field it was copied from, and a missing field is shown as that field's default.
"""
import json
from typing import get_origin

from pydantic import TypeAdapter
from pydantic_core import PydanticUndefined

from docfactory.generation import document_store
from docfactory.generation.bindings import source_field
from docfactory.documentmodels.document_control import DocumentControl
from docfactory.documentmodels.missing_info import MissingInfo
from docfactory.documentmodels.revision_history import RevisionHistory
from docfactory.documentmodels.document_body import DocumentBody
from docfactory.render import RenderError, field_lines, needs_markdown, render_document_control, render_revision_history


def _load(model, key: str):
    value = document_store.stored_model(model, key)
    if value is None:
        raise RenderError(f"Cannot render: no DocumentOutputs row for key {key!r} ({model.__name__} is missing)")
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

    Reads the three rows under `<app_id>.Outputs.<doc_type>`. Raises RenderError, naming the missing key, when one is not there.
    """
    prefix = document_store.prefix(app_id, doc_type)
    control = _load(DocumentControl, f"{prefix}.DocumentControl")
    history = _load(RevisionHistory, f"{prefix}.RevisionHistory")
    body = _load(DocumentBody, prefix)
    return "\n\n".join([render_document_control(control), render_revision_history(history), _render_body(body)]) + "\n"


def render_document_needs(app_id: str, doc_type: str) -> str | None:
    """The needs list of the document as Markdown, from its `.MissingInfo` row; None when there is no row or no gap."""
    info = document_store.stored_model(MissingInfo, f"{document_store.prefix(app_id, doc_type)}.MissingInfo")
    return None if info is None else needs_markdown(app_id, doc_type, info)
