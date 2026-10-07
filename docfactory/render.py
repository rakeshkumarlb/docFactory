"""Renders one document's three stored DocumentOutputs rows to a single deterministic Markdown string.

Same rows in, same bytes out: `render_markdown` only reads what is stored (via `db.get_row`) and formats
it; it never talks to KnowledgeFacts or invents content. A missing row fails with a clear RenderError
instead of producing a blank section.
"""
import json

from docfactory import db
from docfactory.documentmodels.shared.document_control import DocumentControl
from docfactory.documentmodels.shared.missing_info import MissingInfo
from docfactory.documentmodels.shared.revision_history import RevisionHistory
from docfactory.generation.doc_types import DOC_TYPES
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.not_applicable import NotApplicable

# The body model for each document type, from the one table of document types.
BODY_MODELS = {doc_type: spec["model"] for doc_type, spec in DOC_TYPES.items()}

NOT_PROVIDED = "_Not provided._"
ACRONYMS = {"kpi": "KPI", "kpis": "KPIs", "id": "ID", "slo": "SLO", "slos": "SLOs", "sop": "SOP", "smtd": "SMTD", "srs": "SRS", "ci": "CI", "cd": "CD", "rpo": "RPO", "rto": "RTO", "url": "URL"}


def _extra(field) -> dict:
    return field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}


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


def _list_lines(values: list, render_as: str, indent: str) -> list[str]:
    """One line per entry: bullets, or an ordered list when the field is declared `render_as="numbered"`."""
    if render_as == "numbered":
        return [f"{indent}{index}. {value}" for index, value in enumerate(values, start=1)]
    return [f"{indent}- {value}" for value in values]


def _item_lines(item: DocFactoryModel) -> list[str]:
    lines = []
    for name, field in type(item).model_fields.items():
        value = getattr(item, name)
        if isinstance(value, list) and value:
            lines.append(f"  - **{_title(name)}:**")
            lines += _list_lines(value, _extra(field).get("render_as"), "    ")
        elif isinstance(value, list):
            lines.append(f"  - **{_title(name)}:** {NOT_PROVIDED}")
        else:
            text = _scalar_text(value)
            lines.append(f"  - **{_title(name)}:** {text if text else NOT_PROVIDED}")
    return lines


def _table_cell(value) -> str:
    text = ", ".join(str(v) for v in value) if isinstance(value, list) else _scalar_text(value)
    text = (text if text else NOT_PROVIDED).replace("|", "\\|").replace("\n", " ")
    return text


def _item_table(items: list[DocFactoryModel]) -> list[str]:
    fields = list(type(items[0]).model_fields)
    headers = [_title(name) for name in fields]
    lines = [f"| {' | '.join(headers)} |", f"|{'|'.join(['---'] * len(headers))}|"]
    for item in items:
        cells = [_table_cell(getattr(item, name)) for name in fields]
        lines.append(f"| {' | '.join(cells)} |")
    lines.append("")
    return lines


def _field_lines(model: DocFactoryModel, heading_level: int) -> list[str]:
    lines = []
    for name in type(model).model_fields:
        value = getattr(model, name)
        label = _title(name)
        if isinstance(value, DocFactoryModel) and not isinstance(value, NotApplicable):
            lines.append(f"{'#' * heading_level} {label}")
            lines.append("")
            lines += _field_lines(value, heading_level + 1)
            lines.append("")
        elif isinstance(value, list) and value and isinstance(value[0], DocFactoryModel):
            lines.append(f"**{label}:**")
            if _extra(type(model).model_fields[name]).get("render_as") == "table":
                lines.append("")
                lines += _item_table(value)
            else:
                for index, item in enumerate(value, start=1):
                    lines.append(f"{index}.")
                    lines += _item_lines(item)
                lines.append("")
        elif isinstance(value, list):
            lines.append(f"**{label}:**" if value else f"**{label}:** {NOT_PROVIDED}")
            lines += _list_lines(value, _extra(type(model).model_fields[name]).get("render_as"), "")
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


def _gap_line(gap) -> str:
    counts = f" (missing in {gap.missing_in} of {gap.item_count})" if gap.missing_in is not None and gap.item_count is not None else ""
    return f"#{gap.number} `{gap.field}`{counts}"


def render_needs_markdown(app_id: str, doc_type: str) -> str | None:
    """The needs list of `app_id`'s `doc_type` document as Markdown, from its `.MissingInfo` row; None when there is no row or no gap.

    The needs in priority order, grouped by who can answer them (first appearance order), each with the gaps it covers; then every
    gap with its source and example items. Same row in, same bytes out.
    """
    row = db.get_row("DocumentOutputs", f"{app_id}.Outputs.{doc_type}.MissingInfo")
    if row is None:
        return None
    info = MissingInfo.model_validate(json.loads(row["Value"]))
    if not info.gaps:
        return None
    gaps = {gap.number: gap for gap in info.gaps}
    lines = [f"# {app_id} {doc_type}: what is still needed", "",
             f"{len(info.needs)} question(s) covering {len(info.gaps)} gap(s); needs list: {info.needs_origin.value}.", ""]
    audiences = list(dict.fromkeys(need.audience for need in info.needs))
    for audience in audiences:
        lines += [f"## {audience if audience else 'Questions'}", ""]
        for number, need in enumerate(info.needs, start=1):
            if need.audience != audience:
                continue
            lines.append(f"{number}. {need.question}")
            lines.append(f"   - Covers: {', '.join(_gap_line(gaps[n]) for n in need.gaps if n in gaps)}")
        lines.append("")
    lines += ["## Gaps", ""]
    for gap in info.gaps:
        lines.append(f"{gap.number}. `{gap.field}`: {gap.question}")
        counts = f", missing in {gap.missing_in} of {gap.item_count} items" if gap.missing_in is not None and gap.item_count is not None else ""
        lines.append(f"   - Source: `{gap.expected_source}`{counts}")
        lines += [f"   - e.g. {example}" for example in gap.example_items]
    return "\n".join(lines).rstrip("\n") + "\n"
