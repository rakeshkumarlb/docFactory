"""The text of an entity concept file: OKF frontmatter, the entity under `# Value` (the truth), and derived `# Relationships` and `# Evidence`
sections for a human reader. Same record and version, same bytes."""
import json

from docfactory.bundle.fact_file_render import FENCE, VALUE_HEADING
from docfactory.bundle.paths import entity_relpath
from docfactory.models.entity_record import EntityRecord

ENTITY_GENERATOR = "docfactory/entity-merge"


def _text(value: str) -> str:
    """A YAML double-quoted scalar (JSON strings are valid YAML)."""
    return json.dumps(value, ensure_ascii=False)


def _list(values: list[str]) -> str:
    return "[" + ", ".join(_text(v) for v in values) + "]"


def _target(record: EntityRecord, target: str, names: dict[str, str]) -> str:
    if target in names:
        return f"[{names[target]}](/{entity_relpath(record.scope, target)})"
    return target


def render_entity_file(record: EntityRecord, version: int, hashcode: str, timestamp: str, names: dict[str, str] | None = None) -> str:
    """The whole file for `record`. `names` maps entity ids of the scope to their names, so links to known entities resolve."""
    names = names or {}
    resources = list(dict.fromkeys(e.resource for e in record.evidence))
    lines = [f"type: {_text(record.type)}", f"title: {_text(record.name)}"]
    if record.summary:
        lines.append(f"description: {_text(record.summary)}")
    if record.aliases:
        lines.append(f"aliases: {_list(record.aliases)}")
    lines.append(f"tags: {_list(['entity', record.type])}")
    lines.append("sources:" if resources else "sources: []")
    lines += [f"  - resource: {_text(r)}" for r in resources]
    lines += [
        f"generated: {{ by: {_text(ENTITY_GENERATOR)}, at: {_text(timestamp)} }}",
        "verified: []",
        "status: draft",
        f"entity_id: {_text(record.entity_id)}",
        f"scope: {_text(record.scope)}",
        f"version: {version}",
        f"hashcode: {_text(hashcode)}",
    ]
    value = json.dumps(record.model_dump(mode="json"), indent=2, ensure_ascii=False)
    body = [f"{VALUE_HEADING}", "", f"{FENCE}json", value, FENCE]
    if record.links:
        body += ["", "# Relationships", ""] + [f"- {link.relation} {_target(record, link.target, names)}" for link in record.links]
    if record.evidence:
        body += ["", "# Evidence", ""] + [f"- {e.resource} chunk {e.chunk_no}" + (f": {e.heading}" if e.heading else "") for e in record.evidence]
    return "---\n" + "\n".join(lines) + "\n---\n\n" + "\n".join(body) + "\n"
