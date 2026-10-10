"""The revision history of a generated document, maintained by code: one entry per body save that changed the body.

The summary is written by code, never by the LLM: which sections changed and the fact keys and versions they came from. Existing
entries are kept. An unchanged body adds no entry, unless the history is behind the body: the latest entry is not the body's version
(no history yet, or an earlier run saved the body and then stopped before saving its history). Then one entry catches it up.
"""
from docfactory.documentmodels.revision_entry import RevisionEntry
from docfactory.documentmodels.revision_history import RevisionHistory
from docfactory.generation.document_control import OWNER


RECOVERED = "Revision recorded late: an earlier run saved this body version without its revision entry; its changed sections were not kept."


def history_is_behind(existing: RevisionHistory | None, version: str) -> bool:
    """True when `existing` has no revision, or its latest revision is not `version` (the document version of the stored body)."""
    return existing is None or not existing.revisions or existing.revisions[-1].version != version


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
