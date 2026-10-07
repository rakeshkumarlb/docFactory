"""Stores a knowledge fact with its OKF metadata in the KnowledgeFacts row. Called by BaseSaver for entity savers only; no validation here.

OKF lives only in the row's metadata columns; the content is the validated JSON in Value. No file is written."""
import json

from docfactory import clock, db
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
               changed: bool, meta: FactMeta | None) -> None:
    """Write a new or changed fact: the row (a new value is always a draft, unverified, generated now), history when it replaced
    an earlier value (`changed`) and the source index. Without `meta` the metadata is the bare defaults."""
    meta = meta or FactMeta(generated_by=DEFAULT_GENERATED_BY)
    record = FactRecord(
        key=key, value=value, hashcode=hashcode, completeness=score, version=version, app_id=app_id,
        generated_by=meta.generated_by, generated_at=clock.now_iso(), status=FactStatus.DRAFT, **_meta_fields(key, kind, meta),
    )
    frontmatter = render_frontmatter(record, kind, meta)
    okf = {**_columns(record, frontmatter), "Verified": EMPTY_VERIFIED, "Status": record.status.value}
    db.write_fact_row(key, value, hashcode, app_id, score, version, okf, [source.resource for source in meta.sources], changed)


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
