"""Deterministic OKF v0.2 frontmatter (docs/okf/SPEC.md section 4.1 and 5) for one knowledge fact: same inputs, same text."""
import json
import re

from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord


def type_name(model_name: str) -> str:
    """The OKF `type` of a fact: its model name in words, e.g. ApplicationOverview -> 'Application Overview'."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", model_name)


def _text(value: str) -> str:
    """A YAML double-quoted scalar (JSON strings are valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def _source_lines(meta: FactMeta) -> list[str]:
    lines = ["sources:"]
    for source in meta.sources:
        lines.append(f"  - resource: {_text(source.resource)}")
        for name, value in (("id", source.id), ("title", source.title)):
            if value is not None:
                lines.append(f"    {name}: {_text(value)}")
        if source.last_modified is not None:
            lines.append(f"    last_modified: {source.last_modified}")
    return lines


def render_frontmatter(record: FactRecord, kind: str, meta: FactMeta) -> str:
    """The YAML between the `---` lines (ends with a newline). `record` supplies key, version, completeness, trust and lifecycle."""
    lines = [f"type: {_text(kind)}", f"title: {_text(meta.title or record.key)}"]
    if meta.description:
        lines.append(f"description: {_text(meta.description)}")
    if meta.tags:
        lines.append("tags: [" + ", ".join(_text(tag) for tag in meta.tags) + "]")
    if meta.sources:
        lines += _source_lines(meta)
    if record.generated_by:
        at = f", at: {record.generated_at}" if record.generated_at else ""
        lines.append(f"generated: {{ by: {_text(record.generated_by)}{at} }}")
    if record.verified:
        lines.append("verified:")
        lines += [f"  - {{ by: {_text(event.by)}, at: {event.at} }}" for event in record.verified]
    lines.append(f"status: {record.status.value}")
    if record.stale_after:
        lines.append(f"stale_after: {record.stale_after}")
    lines += [f"fact_key: {_text(record.key)}", f"version: {record.version}", f"completeness: {record.completeness:g}"]
    return "\n".join(lines) + "\n"
