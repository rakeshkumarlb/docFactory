"""Stores a knowledge fact with its OKF metadata in the KnowledgeFacts row, then its JSON file under knowledgefacts/. Called by BaseSaver
for entity savers only; no validation here.

OKF lives only in the row's metadata columns; the content is the validated JSON in Value, and the file is a view of that JSON."""
import json

from pydantic import BaseModel

from docfactory import clock, db, fact_files
from docfactory.facts import record_of
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord
from docfactory.models.fact_status import FactStatus
from docfactory.okf_frontmatter import render_frontmatter

DEFAULT_GENERATED_BY = "docfactory/unspecified"
EMPTY_VERIFIED = "[]"


def _json_list(items: list) -> str:
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"))


def _columns(record: FactRecord, frontmatter: str) -> dict:
    return {
        "FactType": record.type,
        "Title": record.title,
        "Description": record.description,
        "Tags": _json_list(record.tags),
        "Sources": _json_list([source.model_dump(mode="json", exclude_none=True) for source in record.sources]),
        "YmlFrontmatter": frontmatter,
        "GeneratedBy": record.generated_by,
        "GeneratedAt": record.generated_at,
        "StaleAfter": record.stale_after,
    }


def _meta_fields(key: str, kind: str, meta: FactMeta) -> dict:
    """The record fields taken from the caller's metadata (the title defaults to the key)."""
    return {"type": kind, "title": meta.title or key, "description": meta.description, "tags": meta.tags,
            "sources": meta.sources, "stale_after": meta.stale_after}


def write_fact(key: str, kind: str, value: str, hashcode: str, app_id: str | None, score: float, version: int,
               changed: bool, meta: FactMeta | None, fact: BaseModel) -> None:
    """Write a new or changed fact: the row (a new value is always a draft, unverified, generated now), history when it replaced
    an earlier value (`changed`), the source index and the fact's files. Without `meta` the metadata is the bare defaults.
    `fact` is the validated object: its JSON file (model field order) and its open questions are written from it."""
    meta = meta or FactMeta(generated_by=DEFAULT_GENERATED_BY)
    record = FactRecord(
        key=key, value=value, hashcode=hashcode, completeness=score, version=version, app_id=app_id,
        generated_by=meta.generated_by, generated_at=clock.now_iso(), status=FactStatus.DRAFT, **_meta_fields(key, kind, meta),
    )
    frontmatter = render_frontmatter(record, kind, meta)
    okf = {**_columns(record, frontmatter), "Verified": EMPTY_VERIFIED, "Status": record.status.value}
    db.write_fact_row(key, value, hashcode, app_id, score, version, okf, [source.resource for source in meta.sources], changed)
    fact_files.write_file(key, fact)


def ensure_file(key: str, fact: BaseModel) -> None:
    """The value is unchanged: (re)write the fact's files only if they are missing or differ."""
    fact_files.write_file(key, fact)


def refresh_metadata(key: str, kind: str, row: dict, meta: FactMeta) -> None:
    """The value is unchanged but a caller supplied metadata: refresh type, title, description, tags, sources, stale_after and the
    frontmatter in place. Value, Hashcode, Version, completeness, status and trust are untouched.
    A row saved before Phase 3 has no generated_by / generated_at yet; it gets the caller's actor and now."""
    stored = record_of(row)
    record = stored.model_copy(update={
        "generated_by": stored.generated_by or meta.generated_by,
        "generated_at": stored.generated_at or clock.now_iso(),
        **_meta_fields(key, kind, meta),
    })
    frontmatter = render_frontmatter(record, kind, meta)
    if _columns(record, frontmatter) == _columns(stored, stored.frontmatter or ""):
        return
    db.update_fact_metadata(key, _columns(record, frontmatter), [source.resource for source in meta.sources])
