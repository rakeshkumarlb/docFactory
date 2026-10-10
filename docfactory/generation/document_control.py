"""The document control of a generated document, derived by code (CLAUDE.md, Phase 4: "Document control and revision history").

Everything is derived for certain or left to Phase 5: the id, title, version label and owner are set by code; the status and the approvers
are kept from the stored row (the Phase 5 approval owns them), the status starts as Draft; the creation date is kept, the last-updated date
moves only when the body changed (or the history had to catch up).
"""
from docfactory.documentmodels.document_control import DocumentControl

OWNER = "docFactory"
DRAFT = "Draft"


def document_version(body_version: int) -> str:
    """The document's own version label while it is a draft: 0.<body row Version>, e.g. 0.3."""
    return f"0.{body_version}"


def next_control(app_id: str, doc_type: str, doc_name: str, existing: DocumentControl | None, changed: bool,
                 body_version: int, today: str) -> DocumentControl:
    """The document control after a run; `changed` is true when the body changed (or the history had to catch up), `existing` is the stored row, None on the first run."""
    return DocumentControl(
        document_id=f"{app_id}-{doc_type}",
        title=f"{app_id} {doc_name}",
        document_version=document_version(body_version),
        status=existing.status if existing is not None and existing.status else DRAFT,
        owner=OWNER,
        approvers=list(existing.approvers) if existing is not None else [],
        created_date=existing.created_date if existing is not None and existing.created_date else today,
        last_updated_date=today if changed or existing is None or not existing.last_updated_date else existing.last_updated_date,
    )
