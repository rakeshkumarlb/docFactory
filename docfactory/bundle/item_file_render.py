"""The text of an item's concept file: OKF frontmatter, the validated JSON under `# Value`, its open questions and its links. Same inputs, same bytes."""
import json

from pydantic import BaseModel

from docfactory.bundle.fact_file_render import DEFAULT_GENERATED_BY, FENCE, VALUE_HEADING
from docfactory.bundle.paths import EXISTING_RESOURCE, fact_relpath, source_relpath
from docfactory.missing_md import missing_md
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord
from docfactory.models.item_record import ItemRecord
from docfactory.okf_frontmatter import render_frontmatter, source_labels, text_of, type_name
from docfactory.open_questions import open_questions


def source_link(resource: str) -> str | None:
    """The bundle-relative link target of the Source concept of the original `resource`, or None for a resource that is not a stored original."""
    if resource == EXISTING_RESOURCE:
        return None
    try:
        return "/" + source_relpath(resource)
    except ValueError:
        return None


def links_text(parent: FactRecord) -> str:
    """The `# Links` section of an item: the fact it is part of and the Sources it derives from (OKF section 6.1, bundle-relative links)."""
    lines = ["# Links", "", f"* Part of [{parent.title or parent.key}](/{fact_relpath(parent.key)})"]
    for source in parent.sources:
        target = source_link(source.resource)
        if target:
            lines.append(f"* Derived from [{source.title or source.resource}]({target.replace(' ', '%20')})")
    return "\n".join(lines) + "\n"


def provenance_text(parent: FactRecord) -> str:
    """The `# Provenance` section of an item: a sentence citing each source of its fact by a footnote keyed to the `sources[].id` (OKF section 5.1). Empty without sources."""
    if not parent.sources:
        return ""
    labels = source_labels(parent.sources)
    cites = "".join(f"[^{label}]" for label in labels)
    notes = [f"[^{label}]: {source.title or source.resource}" + (f", {source.author}" if source.author else "") for source, label in zip(parent.sources, labels)]
    return "\n".join(["# Provenance", "", f"Taken from the documents its fact was extracted from.{cites}", ""] + notes) + "\n"


def render_item_file(parent: FactRecord, item: BaseModel, record: ItemRecord) -> str:
    """The whole file for `record`; `parent` supplies the metadata the item shares with its fact (sources, trust, lifecycle)."""
    kind = type_name(type(item).__name__)
    meta = FactMeta(generated_by=parent.generated_by or DEFAULT_GENERATED_BY, title=record.item_id, tags=[record.field], sources=parent.sources,
                    stale_after=parent.stale_after)
    shadow = parent.model_copy(update={"version": record.version, "completeness": record.completeness, "title": record.item_id, "tags": meta.tags})
    frontmatter = render_frontmatter(shadow, kind, meta)
    frontmatter += (f"item_field: {text_of(record.field)}\nitem_id: {text_of(record.item_id)}\nposition: {record.position}\n"
                    f"hashcode: {json.dumps(record.hashcode)}\n")
    value = json.dumps(json.loads(item.model_dump_json()), indent=2, ensure_ascii=False)
    text = f"---\n{frontmatter}---\n\n{VALUE_HEADING}\n\n{FENCE}json\n{value}\n{FENCE}\n"
    questions = open_questions(item)
    if questions:
        text += "\n" + missing_md(f"{parent.key} {record.field} {record.item_id}", questions)
    for heading, name in (("Additional information", "additional_information"), ("Evidence", "evidence")):
        entries = getattr(item, name, None)
        if entries:
            text += f"\n# {heading}\n\n" + "\n".join(f"* {entry}" for entry in entries) + "\n"
    provenance = provenance_text(parent)
    return text + "\n" + (provenance + "\n" if provenance else "") + links_text(parent)


def items_section(parent_dir_links: list[tuple[str, list[tuple[str, str]]]]) -> str:
    """The `# Items` section of a parent concept: per list field, a link to each item's concept file. `parent_dir_links` = [(field, [(item id, relpath)])]."""
    lines = ["# Items", ""]
    for field, items in parent_dir_links:
        lines += [f"## {field}", ""] + [f"* [{item_id}](/{relpath.replace(' ', '%20')})" for item_id, relpath in items] + [""]
    return "\n".join(lines).rstrip("\n") + "\n"

