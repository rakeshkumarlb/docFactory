"""The text of a Source concept file: OKF frontmatter only (no body). Same record in, same bytes out."""
import json
import posixpath

from docfactory.models.source_record import SourceRecord

SOURCE_TYPE = "Source"
INGESTION_ACTOR = "docfactory/ingestion"


def _text(value: str) -> str:
    """A YAML double-quoted scalar (JSON strings are valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def render_source_file(record: SourceRecord) -> str:
    """The whole file for `record`."""
    lines = [
        f"type: {_text(SOURCE_TYPE)}",
        f"title: {_text(posixpath.basename(record.path))}",
        f"resource: {_text(record.path)}",
        *([f"author: {_text(record.author)}"] if record.author else []),
        f"generated: {{ by: {_text(INGESTION_ACTOR)}, at: {_text(record.timestamp)} }}",
        f"hashcode: {_text(record.hashcode)}",
        f"version: {record.version}",
        "chunks:" if record.chunks else "chunks: []",
    ]
    lines += [f"  - {{ chunk: {c.chunk_no}, hash: {_text(c.text_hash)}, heading: {_text(c.heading)} }}" for c in record.chunks]
    lines.append("chunk_tags:" if record.tags else "chunk_tags: []")
    lines += [
        f"  - {{ chunk: {t.chunk_no}, entity: {_text(t.entity)}, origin: {_text(t.origin)}, score: {t.score}, evidence: {_text(t.evidence)} }}"
        for t in record.tags
    ]
    return "---\n" + "\n".join(lines) + "\n---\n"
