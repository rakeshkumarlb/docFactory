"""The revision history of a generated document, maintained by code: one entry per body save that changed the body.

The summary is written by code, never by the LLM: which sections changed and the fact keys and versions they came from. Existing
entries are kept. An unchanged body adds no entry, except when no history exists yet (a body saved before generate kept its history).
"""
import json

from docfactory import db
from docfactory.build import bound_fields, fact_key
from docfactory.documentmodels.shared.revision_entry import RevisionEntry
from docfactory.documentmodels.shared.revision_history import RevisionHistory
from docfactory.generation.document_control import OWNER


def changed_sections(old_body_json: str | None, new_body) -> list[str]:
    """The body's top-level sections whose content differs from the stored body; every section when there was none."""
    new = new_body.model_dump(mode="json")
    if old_body_json is None:
        return list(new)
    old = json.loads(old_body_json)
    return [name for name in new if old.get(name) != new[name]]


def section_sources(document_model, app_id: str) -> dict[str, list[str]]:
    """Per top-level section, the facts it is built from as '<key> v<version>', or '<key> (not available)', in template order."""
    sources: dict[str, list[str]] = {}
    for path, _, binding in bound_fields(document_model):
        section = path.split(".")[0]
        key = fact_key(app_id, binding.partition(".")[0])
        row = db.get_row("KnowledgeFacts", key)
        text = f"{key} v{row['Version']}" if row else f"{key} (not available)"
        if text not in sources.setdefault(section, []):
            sources[section].append(text)
    return sources


def revision_summary(created: bool, sections: list[str], sources: dict[str, list[str]]) -> str:
    """'Generated from ...' for a first body, else 'Changed sections: <section> (from <key> v<n>), ...'."""
    if created:
        keys = list(dict.fromkeys(text for section in sources for text in sources[section]))
        return f"Generated from {', '.join(keys)}."
    parts = [f"{section} (from {', '.join(sources.get(section, [])) or 'no fact'})" for section in sections]
    return f"Changed sections: {'; '.join(parts)}." if parts else "Regenerated; no section changed."


def next_history(existing: RevisionHistory | None, add_entry: bool, version: str, summary: str, today: str) -> tuple[RevisionHistory, RevisionEntry | None]:
    """The history with one new entry appended when `add_entry` (or when there is no history yet); returns (history, the entry or None)."""
    if not add_entry and existing is not None:
        return existing, None
    entry = RevisionEntry(version=version, date=today, author=OWNER, summary=summary)
    revisions = list(existing.revisions) if existing is not None else []
    notes = existing.notes if existing is not None else ""
    return RevisionHistory(revisions=revisions + [entry], notes=notes), entry
