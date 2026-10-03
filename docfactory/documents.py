"""Typed read side of DocumentOutputs: rows come back as DocumentRecord."""
from docfactory import db
from docfactory.models.document_record import DocumentRecord

TABLE = "DocumentOutputs"


def record_of(row: dict) -> DocumentRecord:
    return DocumentRecord(
        key=row["DocumentKey"], value=row["Value"], hashcode=row["Hashcode"],
        completeness=row["Completeness"], version=row["Version"], app_id=row["AppID"],
    )


def get_document(key: str) -> DocumentRecord | None:
    """The stored document row for `key` (a body, `.DocumentControl` or `.RevisionHistory` key), or None."""
    row = db.get_row(TABLE, key)
    return record_of(row) if row else None


def list_documents(app_id: str | None = None) -> list[DocumentRecord]:
    """All stored document rows ordered by key; with `app_id`, only that application's rows."""
    return [record_of(row) for row in db.list_rows(TABLE, app_id)]
