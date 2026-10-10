"""What the revision history of a document needs: the sections that changed and the facts each one comes from."""
import json

from docfactory import db
from docfactory.build import fact_key
from docfactory.documentmodels.document_body import DocumentBody
from docfactory.models.document_template import DocumentTemplate


def changed_section_ids(old_body_json: str | None, new_body: DocumentBody) -> list[str]:
    """The ids of the sections whose content differs from the stored body, in template order; every section when there was none."""
    new = {section.id: section.model_dump(mode="json") for section in new_body.sections}
    if old_body_json is None:
        return list(new)
    old = {section["id"]: section for section in json.loads(old_body_json)["sections"]}
    return [section_id for section_id, section in new.items() if old.get(section_id) != section]


def template_sources(template: DocumentTemplate, app_id: str) -> dict[str, list[str]]:
    """Per section id, the facts it is built from as '<key> v<version>', or '<key> (not available)', in template order."""
    sources: dict[str, list[str]] = {}
    for section in template.sections:
        for field in section.fields:
            key = fact_key(app_id, field.binding.partition(".")[0])
            row = db.get_row("KnowledgeFacts", key)
            text = f"{key} v{row['Version']}" if row else f"{key} (not available)"
            if text not in sources.setdefault(section.id, []):
                sources[section.id].append(text)
    return sources
