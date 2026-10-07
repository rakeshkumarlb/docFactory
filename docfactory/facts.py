"""Typed read side of KnowledgeFacts: rows come back as FactRecord."""
import json

from docfactory import db
from docfactory.models.fact_record import FactRecord
from docfactory.models.fact_source import FactSource
from docfactory.models.fact_status import FactStatus
from docfactory.models.fact_verification import FactVerification

TABLE = "KnowledgeFacts"


def record_of(row: dict) -> FactRecord:
    return FactRecord(
        key=row["FactKey"],
        value=row["Value"],
        hashcode=row["Hashcode"],
        completeness=row["Completeness"],
        version=row["Version"],
        app_id=row["AppID"],
        type=row["FactType"],
        title=row["Title"],
        description=row["Description"],
        tags=json.loads(row["Tags"]),
        sources=[FactSource.model_validate(source) for source in json.loads(row["Sources"])],
        frontmatter=row["YmlFrontmatter"],
        generated_by=row["GeneratedBy"],
        generated_at=row["GeneratedAt"],
        verified=[FactVerification.model_validate(event) for event in json.loads(row["Verified"])],
        status=FactStatus(row["Status"]),
        stale_after=row["StaleAfter"],
    )


def get_fact(key: str) -> FactRecord | None:
    """The stored fact for `key`, or None."""
    row = db.get_row(TABLE, key)
    return record_of(row) if row else None


def list_facts(app_id: str | None = None) -> list[FactRecord]:
    """All stored facts ordered by key; with `app_id`, only that application's facts."""
    return [record_of(row) for row in db.list_rows(TABLE, app_id)]


def list_facts_by_source(resource: str) -> list[FactRecord]:
    """The facts whose sources name `resource` (a DocStore path): the facts to re-check when that file changes."""
    return [fact for key in db.list_fact_keys_by_source(resource) if (fact := get_fact(key)) is not None]
