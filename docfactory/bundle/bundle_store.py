from pathlib import Path

from pydantic import ValidationError

from docfactory import clock
from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_index import write_index
from docfactory.bundle.bundle_log import append_log
from docfactory.bundle.fact_file_parse import parse_fact_file
from docfactory.bundle.fact_file_render import DEFAULT_GENERATED_BY, render_fact_file
from docfactory.bundle.fact_registry import FACT_SPECS
from docfactory.bundle.file_io import put_text
from docfactory.bundle.key_check import check_key
from docfactory.bundle.paths import NON_FACT_DIRS, RESERVED_FILES, SUFFIX, bundle_root, fact_relpath
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.completeness import completeness
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord
from docfactory.models.fact_status import FactStatus
from docfactory.models.save_action import SaveAction
from docfactory.models.save_error import SaveError
from docfactory.models.save_result import SaveResult
from docfactory.okf_frontmatter import type_name
from docfactory.validation_errors import validation_errors


def _rejected(key, errors: list[SaveError]) -> SaveResult:
    return SaveResult(ok=False, key=str(key) or "(empty)", action=SaveAction.REJECTED, errors=errors)


class BundleStore:
    """The OKF bundle of knowledge facts: the only writer and reader of the fact concept files.

    A fact is one markdown file (OKF frontmatter + its validated JSON). `write_fact` validates the payload with the entity model, hashes it,
    versions it and writes the file only when something changed; `read_fact` re-validates the JSON and refuses a file whose hash no longer
    matches (it was edited by hand). Index and log are kept up to date by code.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else bundle_root()

    def _path(self, key: str) -> Path:
        return self.root / fact_relpath(key)

    def read_fact(self, key: str) -> FactRecord | None:
        """The stored, re-validated fact for `key`, or None when there is no file. BundleError when the file cannot be trusted."""
        path = self._path(key)
        if not path.is_file():
            return None
        return self._checked(self._parse(path), key)

    def list_facts(self, app_id: str | None = None) -> list[FactRecord]:
        """All stored facts ordered by key (each re-validated); with `app_id`, only that application's facts."""
        return [self._checked(record, record.key) for record in self._scan() if app_id is None or record.app_id == app_id]

    def list_facts_by_source(self, resource: str) -> list[FactRecord]:
        """The facts whose sources name `resource`: the facts to re-check when that file changes."""
        return [record for record in self.list_facts() if any(source.resource == resource for source in record.sources)]

    def write_fact(self, key: str, payload, meta: FactMeta | None = None) -> SaveResult:
        """Save the whole object under `key`. Never raises for bad input: a rejection is returned and nothing is written.

        Same hash = UNCHANGED (the metadata of `meta` is refreshed in place, the version stays); a new value is CREATED (version 1) or
        UPDATED (version + 1), always a draft, unverified, generated now by `meta.generated_by`.
        """
        entity, key_errors = check_key(key)
        if key_errors:
            return _rejected(key, key_errors)
        model = FACT_SPECS[entity]["model"]
        try:
            instance = model.model_validate(payload)
        except ValidationError as error:
            return _rejected(key, validation_errors(model, error))
        value = canonical_json(instance.model_dump(mode="json"))
        hashcode = sha256_hex(value)
        try:
            existing = self.read_fact(key)
        except BundleError as error:
            return _rejected(key, [SaveError(
                path="key", message=str(error), error_type="bundle_file_untrusted", received=None,
                expected="a fact file written by the system", field_description=None,
                question="The stored file was changed outside the system: restore it from version control or remove it, then save again.",
            )])

        if existing is not None and existing.hashcode == hashcode:
            record = existing if meta is None else self._with_meta(existing, key, meta)
            if self._store(record, instance):
                self._refresh_index()
            return SaveResult(ok=True, key=key, action=SaveAction.UNCHANGED, version=existing.version, hashcode=hashcode, completeness=existing.completeness)

        action, version = (SaveAction.CREATED, 1) if existing is None else (SaveAction.UPDATED, existing.version + 1)
        now = clock.now_iso()
        meta = meta or FactMeta(generated_by=DEFAULT_GENERATED_BY)
        score = completeness(instance)
        record = FactRecord(
            key=key, value=value, hashcode=hashcode, completeness=score, version=version, app_id=None if key.startswith("Shared.") else key.split(".")[0],
            type=type_name(model.__name__), title=meta.title or key, description=meta.description, tags=meta.tags, sources=meta.sources,
            generated_by=meta.generated_by, generated_at=now, status=FactStatus.DRAFT, stale_after=meta.stale_after,
        )
        self._store(record, instance)
        append_log(self.root, now[:10], "Creation" if action == SaveAction.CREATED else "Update", key, fact_relpath(key), version, meta.generated_by)
        self._refresh_index()
        return SaveResult(ok=True, key=key, action=action, version=version, hashcode=hashcode, completeness=score)

    def _store(self, record: FactRecord, instance) -> bool:
        return put_text(self._path(record.key), render_fact_file(record, instance))

    def _with_meta(self, stored: FactRecord, key: str, meta: FactMeta) -> FactRecord:
        """`stored` with the caller's title, description, tags, sources and stale_after (value, version, trust and lifecycle untouched)."""
        return stored.model_copy(update={
            "generated_by": stored.generated_by or meta.generated_by, "generated_at": stored.generated_at or clock.now_iso(),
            "title": meta.title or key, "description": meta.description, "tags": meta.tags, "sources": meta.sources, "stale_after": meta.stale_after,
        })

    def _refresh_index(self) -> None:
        write_index(self.root, self._scan())

    def _parse(self, path: Path) -> FactRecord:
        try:
            return parse_fact_file(path.read_text(encoding="utf-8"))
        except BundleError as error:
            raise BundleError(f"{path.relative_to(self.root).as_posix()}: {error}") from error

    def _scan(self) -> list[FactRecord]:
        """Every fact file of the bundle parsed (not yet re-validated), ordered by key."""
        records = []
        for path in sorted(p for p in self.root.rglob("*" + SUFFIX) if p.is_file()) if self.root.is_dir() else []:
            parts = path.relative_to(self.root).parts
            if len(parts) < 2 or parts[1] in NON_FACT_DIRS or parts[-1] in RESERVED_FILES:
                continue
            records.append(self._parse(path))
        return sorted(records, key=lambda record: record.key)

    def _checked(self, record: FactRecord, key: str) -> FactRecord:
        """`record` once its JSON validates against the entity model and hashes to the stored hashcode, else BundleError."""
        entity, key_errors = check_key(record.key)
        if key_errors:
            raise BundleError(f"{record.key}: {key_errors[0].message}")
        model = FACT_SPECS[entity]["model"]
        try:
            value = canonical_json(model.model_validate_json(record.value).model_dump(mode="json"))
        except ValidationError as error:
            raise BundleError(f"{record.key}: the stored JSON no longer validates against {model.__name__} ({error.error_count()} errors)") from error
        if sha256_hex(value) != record.hashcode:
            raise BundleError(f"{record.key}: the stored JSON does not match its hashcode; the file was edited outside the system")
        return record.model_copy(update={"value": value})
