"""Deterministic OKF v0.2 frontmatter (docs/okf/SPEC.md section 4.1 and 5) for one knowledge fact: same inputs, same text."""
import json
import re

from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord
from docfactory.models.fact_source import FactSource


def type_name(model_name: str) -> str:
    """The OKF `type` of a fact: its model name in words, e.g. ApplicationOverview -> 'Application Overview'."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", model_name)


def text_of(value: str) -> str:
    """A YAML double-quoted scalar (JSON strings are valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def source_labels(sources: list[FactSource]) -> list[str]:
    """The stable label of each source, the join key of footnotes (OKF section 5.1): its own id, else its file name in lower case with '-' for other characters; repeats get '-2', '-3', ..."""
    seen: dict[str, int] = {}
    labels = []
    for source in sources:
        base = source.id or re.sub(r"[^a-z0-9]+", "-", source.resource.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()).strip("-") or "source"
        seen[base] = seen.get(base, 0) + 1
        labels.append(base if seen[base] == 1 else f"{base}-{seen[base]}")
    return labels


def _source_lines(meta: FactMeta) -> list[str]:
    lines = ["sources:"]
    for source, label in zip(meta.sources, source_labels(meta.sources)):
        lines.append(f"  - resource: {text_of(source.resource)}")
        for name, value in (("id", label), ("title", source.title), ("author", source.author)):
            if value is not None:
                lines.append(f"    {name}: {text_of(value)}")
        if source.last_modified is not None:
            lines.append(f"    last_modified: {source.last_modified}")
    return lines


def render_frontmatter(record: FactRecord, kind: str, meta: FactMeta) -> str:
    """The YAML between the `---` lines (ends with a newline). `record` supplies key, version, completeness, trust and lifecycle."""
    lines = [f"type: {text_of(kind)}", f"title: {text_of(meta.title or record.key)}"]
    if meta.description:
        lines.append(f"description: {text_of(meta.description)}")
    if meta.tags:
        lines.append("tags: [" + ", ".join(text_of(tag) for tag in meta.tags) + "]")
    if meta.sources:
        lines += _source_lines(meta)
    if record.generated_by:
        at = f", at: {record.generated_at}" if record.generated_at else ""
        lines.append(f"generated: {{ by: {text_of(record.generated_by)}{at} }}")
    if record.verified:
        lines.append("verified:")
        lines += [f"  - {{ by: {text_of(event.by)}, at: {event.at} }}" for event in record.verified]
    lines.append(f"status: {record.status.value}")
    if record.stale_after:
        lines.append(f"stale_after: {record.stale_after}")
    lines += [f"fact_key: {text_of(record.key)}", f"version: {record.version}", f"completeness: {record.completeness:g}"]
    return "\n".join(lines) + "\n"
