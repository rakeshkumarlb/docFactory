"""Renders one document's three stored DocumentOutputs rows to a single deterministic Markdown string.

Same rows in, same bytes out: `render_markdown` only reads what is stored (via `db.get_row`) and formats
it; it never talks to KnowledgeFacts or invents content. A missing row fails with a clear RenderError
instead of producing a blank section.
"""
import json

from docfactory import db
from docfactory.documentmodels.document_control import DocumentControl
from docfactory.documentmodels.overview_document import OverviewDocument
from docfactory.documentmodels.revision_history import RevisionHistory
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.not_applicable import NotApplicable

# The body model for each document type. A registry built from the document savers' key patterns is Phase 2.
BODY_MODELS = {"Overview": OverviewDocument}

NOT_PROVIDED = "_Not provided._"
ACRONYMS = {"kpi": "KPI", "kpis": "KPIs", "id": "ID", "slo": "SLO", "slos": "SLOs"}


class RenderError(Exception):
    """Raised when render_markdown cannot find a DocumentOutputs row it needs."""


def _title(name: str) -> str:
    return " ".join(ACRONYMS.get(word, word.capitalize()) for word in name.split("_"))


def _load(model_cls, key: str):
    row = db.get_row("DocumentOutputs", key)
    if row is None:
        raise RenderError(f"Cannot render: no DocumentOutputs row for key {key!r} ({model_cls.__name__} is missing)")
    return model_cls.model_validate(json.loads(row["Value"]))


def _scalar_text(value) -> str:
    if isinstance(value, NotApplicable):
        return f"_N/A — {value.reason}_"
    if value in (None, ""):
        return NOT_PROVIDED
    return str(value)


def _item_lines(item: DocFactoryModel) -> list[str]:
    lines = []
    for name in type(item).model_fields:
        value = getattr(item, name)
        text = ", ".join(str(v) for v in value) if isinstance(value, list) else _scalar_text(value)
        lines.append(f"  - **{_title(name)}:** {text if text else NOT_PROVIDED}")
    return lines


def _field_lines(model: DocFactoryModel, heading_level: int) -> list[str]:
    lines = []
    for name in type(model).model_fields:
        value = getattr(model, name)
        label = _title(name)
        if isinstance(value, DocFactoryModel):
            lines.append(f"{'#' * heading_level} {label}")
            lines.append("")
            lines += _field_lines(value, heading_level + 1)
            lines.append("")
        elif isinstance(value, list) and value and isinstance(value[0], DocFactoryModel):
            lines.append(f"**{label}:**")
            for index, item in enumerate(value, start=1):
                lines.append(f"{index}.")
                lines += _item_lines(item)
            lines.append("")
        elif isinstance(value, list):
            lines.append(f"**{label}:**" if value else f"**{label}:** {NOT_PROVIDED}")
            lines += [f"- {item}" for item in value]
            lines.append("")
        else:
            lines.append(f"**{label}:** {_scalar_text(value)}")
            lines.append("")
    return lines


def _render_document_control(control: DocumentControl) -> str:
    lines = [
        f"# {control.title}",
        "",
        f"- **Document ID:** {control.document_id}",
        f"- **Version:** {_scalar_text(control.document_version)}",
        f"- **Status:** {_scalar_text(control.status)}",
        f"- **Owner:** {_scalar_text(control.owner)}",
        f"- **Approvers:** {', '.join(control.approvers) if control.approvers else NOT_PROVIDED}",
        f"- **Created:** {_scalar_text(control.created_date)}",
        f"- **Last Updated:** {_scalar_text(control.last_updated_date)}",
    ]
    return "\n".join(lines)


def _render_revision_history(history: RevisionHistory) -> str:
    lines = ["## Revision History", ""]
    if history.revisions:
        lines += ["| Version | Date | Author | Summary |", "|---|---|---|---|"]
        lines += [f"| {r.version} | {r.date} | {r.author or '-'} | {r.summary} |" for r in history.revisions]
    else:
        lines.append(NOT_PROVIDED)
    if history.notes:
        lines += ["", history.notes]
    return "\n".join(lines)


def _render_body(body: DocFactoryModel) -> str:
    return "\n".join(_field_lines(body, heading_level=2)).rstrip("\n")


def render_markdown(app_id: str, doc_type: str) -> str:
    """The full Markdown for `app_id`'s `doc_type` document: document control, revision history, then body.

    Reads the three DocumentOutputs rows under `<app_id>.Outputs.<doc_type>`. Raises RenderError, naming
    the missing key, when any of the three rows is not there.
    """
    body_model = BODY_MODELS.get(doc_type)
    if body_model is None:
        raise RenderError(f"render_markdown does not know the body model for doc_type {doc_type!r}; add it to BODY_MODELS")
    prefix = f"{app_id}.Outputs.{doc_type}"
    control = _load(DocumentControl, f"{prefix}.DocumentControl")
    history = _load(RevisionHistory, f"{prefix}.RevisionHistory")
    body = _load(body_model, prefix)
    sections = [_render_document_control(control), _render_revision_history(history), _render_body(body)]
    return "\n\n".join(sections) + "\n"
