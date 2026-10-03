"""Stores a knowledge fact with its OKF metadata and bundle file. Called by BaseSaver for entity savers only; no validation here."""
from docfactory import clock, db
from docfactory.bundle import file_path_of, file_text, write_file
from docfactory.facts import record_of
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord
from docfactory.models.fact_status import FactStatus
from docfactory.okf_body import render_body
from docfactory.okf_frontmatter import render_frontmatter

DEFAULT_GENERATED_BY = "docfactory/unspecified"
EMPTY_VERIFIED = "[]"


def _columns(record: FactRecord, frontmatter: str) -> dict:
    return {
        "FilePath": record.file_path,
        "YmlFrontmatter": frontmatter,
        "GeneratedBy": record.generated_by,
        "GeneratedAt": record.generated_at,
        "StaleAfter": record.stale_after,
    }


def _write_bundle_file(record: FactRecord, frontmatter: str, meta: FactMeta) -> None:
    write_file(record.file_path, file_text(frontmatter, render_body(meta.title or record.key, record.value)))


def write_fact(key: str, kind: str, value: str, hashcode: str, app_id: str | None, score: float, version: int,
               changed: bool, meta: FactMeta | None) -> None:
    """Write a new or changed fact: the row (a new value is always a draft, unverified, generated now), history when it replaced
    an earlier value (`changed`), the source index and the bundle file. Without `meta` the metadata is the bare defaults."""
    meta = meta or FactMeta(generated_by=DEFAULT_GENERATED_BY)
    record = FactRecord(
        key=key, value=value, hashcode=hashcode, completeness=score, version=version, app_id=app_id,
        file_path=file_path_of(key), generated_by=meta.generated_by, generated_at=clock.now_iso(),
        status=FactStatus.DRAFT, stale_after=meta.stale_after,
    )
    frontmatter = render_frontmatter(record, kind, meta)
    okf = {**_columns(record, frontmatter), "Verified": EMPTY_VERIFIED, "Status": record.status.value}
    db.write_fact_row(key, value, hashcode, app_id, score, version, okf, [source.resource for source in meta.sources], changed)
    _write_bundle_file(record, frontmatter, meta)


def refresh_metadata(key: str, kind: str, row: dict, meta: FactMeta) -> None:
    """The value is unchanged but a caller supplied metadata: refresh title, description, tags, sources, stale_after, the
    frontmatter and the bundle file in place. Value, Hashcode, Version, completeness, status and trust are untouched.
    A row saved before Phase 3 has no generated_by / generated_at yet; it gets the caller's actor and now."""
    stored = record_of(row)
    record = stored.model_copy(update={
        "file_path": stored.file_path or file_path_of(key),
        "generated_by": stored.generated_by or meta.generated_by,
        "generated_at": stored.generated_at or clock.now_iso(),
        "stale_after": meta.stale_after,
    })
    frontmatter = render_frontmatter(record, kind, meta)
    if frontmatter == stored.frontmatter:
        return
    db.update_fact_metadata(key, _columns(record, frontmatter), [source.resource for source in meta.sources])
    _write_bundle_file(record, frontmatter, meta)
