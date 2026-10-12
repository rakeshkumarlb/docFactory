import json
import shutil
from pathlib import Path

from pydantic import ValidationError

from docfactory import clock
from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_index import write_index
from docfactory.bundle.bundle_log import append_log
from docfactory.bundle.entity_index import entity_index_text
from docfactory.bundle.fact_file_parse import parse_fact_file
from docfactory.bundle.fact_file_render import DEFAULT_GENERATED_BY, render_fact_file
from docfactory.bundle.fact_registry import FACT_SPECS
from docfactory.bundle.file_io import put_text
from docfactory.bundle.item_file_parse import parse_item_file
from docfactory.bundle.item_file_render import items_section, render_item_file
from docfactory.bundle.item_layout import entity_dir, item_id_of, item_relpath, item_slugs, split_fields
from docfactory.bundle.key_check import check_key
from docfactory.bundle.paths import NON_FACT_DIRS, RESERVED_FILES, SUFFIX, bundle_root, fact_relpath
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.completeness import completeness
from docfactory.models.fact_meta import FactMeta
from docfactory.models.fact_record import FactRecord
from docfactory.models.fact_status import FactStatus
from docfactory.models.item_record import ItemRecord
from docfactory.models.save_action import SaveAction
from docfactory.models.save_error import SaveError
from docfactory.models.save_result import SaveResult
from docfactory.okf_frontmatter import type_name
from docfactory.validation_errors import validation_errors

ITEM_INDEX = "index.md"


def _rejected(key, errors: list[SaveError]) -> SaveResult:
    return SaveResult(ok=False, key=str(key) or "(empty)", action=SaveAction.REJECTED, errors=errors)


class BundleStore:
    """The OKF bundle of knowledge facts: the only writer and reader of the fact concept files.

    A fact is one parent concept file (OKF frontmatter + its validated JSON) plus, for every list of models in it (requirements, environments,
    alerts, ...), one concept file per item under the fact's own folder. `write_fact` validates the whole object with the entity model, hashes it,
    versions it and writes only what changed; `read_fact` assembles the object from the parent and its items, re-validates it and refuses a file
    whose hash no longer matches (it was edited by hand). So the fact is a view over its concepts: callers still save and read the whole object.
    Index and log are kept up to date by code.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else bundle_root()

    def _path(self, key: str) -> Path:
        return self.root / fact_relpath(key)

    def read_fact(self, key: str) -> FactRecord | None:
        """The stored, re-validated fact for `key` (assembled from its items), or None when there is no file. BundleError when a file cannot be trusted."""
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

    def list_items(self, key: str, field: str | None = None) -> list[ItemRecord]:
        """The stored items of the fact `key` (each re-validated against its hash), ordered by list field then position; with `field`, only that list. Empty when none."""
        entity, key_errors = check_key(key)
        if key_errors:
            raise BundleError(f"{key}: {key_errors[0].message}")
        found = self._items_of(key, split_fields(FACT_SPECS[entity]["model"]))
        return [item for name, items in found.items() if field in (None, name) for item in items]

    def write_fact(self, key: str, payload, meta: FactMeta | None = None) -> SaveResult:
        """Save the whole object under `key`. Never raises for bad input: a rejection is returned and nothing is written.

        Same hash = UNCHANGED (the metadata of `meta` is refreshed in place, the version stays); a new value is CREATED (version 1) or
        UPDATED (version + 1), always a draft, unverified, generated now by `meta.generated_by`. Each list of models is written as one item
        concept per item (an item whose value is unchanged keeps its version; an item no longer in the list is removed).
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
            if self._store(record, instance)[0]:
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
        counts = self._store(record, instance)[1]
        detail = f" (items +{counts[0]} ~{counts[1]} -{counts[2]})" if any(counts) else ""
        append_log(self.root, now[:10], "Creation" if action == SaveAction.CREATED else "Update", key, fact_relpath(key), version, meta.generated_by, detail)
        self._refresh_index()
        return SaveResult(ok=True, key=key, action=action, version=version, hashcode=hashcode, completeness=score)

    def delete_fact(self, key: str, actor: str = DEFAULT_GENERATED_BY) -> bool:
        """Remove the fact `key` with all its items and record a Deprecation in the log. False, touching nothing, when there is no such fact."""
        _, key_errors = check_key(key)
        path = self._path(key) if not key_errors else None
        if path is None or not path.is_file():
            return False
        version = self._parse(path).version
        path.unlink()
        folder = self.root / entity_dir(key)
        if folder.is_dir():
            shutil.rmtree(folder)
        append_log(self.root, clock.now_iso()[:10], "Deprecation", key, fact_relpath(key), version, actor, " (removed)")
        self._refresh_index()
        return True

    # --- writing -----------------------------------------------------------------------------------------------------------------------

    def _store(self, record: FactRecord, instance) -> tuple[bool, tuple[int, int, int]]:
        """Write the items of `instance` and then its parent concept. Returns (anything written, (items added, changed, removed))."""
        active = {name: items for name in split_fields(type(instance)) if isinstance(items := getattr(instance, name), list) and items}
        written, counts, links = self._sync_items(record, active)
        parent = render_fact_file(record, instance, frozenset(active), items_section(links) if links else "")
        return put_text(self._path(record.key), parent) or written, counts

    def _sync_items(self, record: FactRecord, active: dict) -> tuple[bool, tuple[int, int, int], list]:
        """One concept file per item of the `active` lists, stale item files removed, the folder index refreshed."""
        changed, added, edited, links, wanted = False, 0, 0, [], set()
        for field, items in active.items():
            ids = [item_id_of(item) for item in items]
            entries = []
            for position, (item, item_id, stem) in enumerate(zip(items, ids, item_slugs(ids)), 1):
                relpath = item_relpath(record.key, field, stem)
                value = canonical_json(item.model_dump(mode="json"))
                digest = sha256_hex(value)
                old = self._old_item(relpath)
                version = 1 if old is None else old.version if old.hashcode == digest else old.version + 1
                added += old is None
                edited += old is not None and old.hashcode != digest
                item_record = ItemRecord(parent_key=record.key, field=field, item_id=item_id, position=position, value=value, hashcode=digest,
                                         version=version, completeness=completeness(item), relpath=relpath)
                changed |= put_text(self.root / relpath, render_item_file(record, item, item_record))
                wanted.add(self.root / relpath)
                entries.append((item_id, relpath))
            links.append((field, entries))
        removed = self._remove_stale(record.key, wanted)
        index = self.root / entity_dir(record.key) / ITEM_INDEX
        if links:
            changed |= put_text(index, entity_index_text(record.title or record.key, links))
        elif index.is_file():
            index.unlink()
            changed = True
        return changed or bool(removed), (added, edited, removed), links

    def _old_item(self, relpath: str) -> ItemRecord | None:
        """The item stored at `relpath` (only its bookkeeping is used), or None when there is none or the file is unreadable (it is about to be overwritten)."""
        path = self.root / relpath
        try:
            return parse_item_file(path.read_text(encoding="utf-8"), relpath) if path.is_file() else None
        except BundleError:
            return None

    def _remove_stale(self, key: str, wanted: set) -> int:
        """Delete the item files of `key` that are not in `wanted` (items that left the fact); empty list folders go with them. Returns how many files went."""
        folder = self.root / entity_dir(key)
        removed = 0
        if not folder.is_dir():
            return 0
        for path in sorted(folder.glob(f"*/*{SUFFIX}")):
            if path not in wanted:
                path.unlink()
                removed += 1
        for sub in sorted(p for p in folder.glob("*") if p.is_dir()):
            if not any(sub.iterdir()):
                sub.rmdir()
        return removed

    def _with_meta(self, stored: FactRecord, key: str, meta: FactMeta) -> FactRecord:
        """`stored` with the caller's title, description, tags, sources and stale_after (value, version, trust and lifecycle untouched)."""
        return stored.model_copy(update={
            "generated_by": stored.generated_by or meta.generated_by, "generated_at": stored.generated_at or clock.now_iso(),
            "title": meta.title or key, "description": meta.description, "tags": meta.tags, "sources": meta.sources, "stale_after": meta.stale_after,
        })

    def _refresh_index(self) -> None:
        write_index(self.root, self._scan())

    # --- reading -----------------------------------------------------------------------------------------------------------------------

    def _parse(self, path: Path) -> FactRecord:
        try:
            return parse_fact_file(path.read_text(encoding="utf-8"))
        except BundleError as error:
            raise BundleError(f"{path.relative_to(self.root).as_posix()}: {error}") from error

    def _scan(self) -> list[FactRecord]:
        """Every parent fact file of the bundle parsed (not yet re-validated), ordered by key. Item files and indexes are not facts."""
        records = []
        for path in sorted(p for p in self.root.rglob("*" + SUFFIX) if p.is_file()) if self.root.is_dir() else []:
            parts = path.relative_to(self.root).parts
            if len(parts) < 2 or parts[1] in NON_FACT_DIRS or parts[-1] in RESERVED_FILES or any(part in FACT_SPECS for part in parts[:-1]):
                continue
            records.append(self._parse(path))
        return sorted(records, key=lambda record: record.key)

    def _items_of(self, key: str, split: dict) -> dict[str, list[ItemRecord]]:
        """The stored items of each list field of `key`, in list order; each file must validate against its item model and hash to its own hashcode."""
        found = {}
        for field, item_model in split.items():
            folder = self.root / entity_dir(key) / field
            rows = []
            for path in sorted(folder.glob(f"*{SUFFIX}")) if folder.is_dir() else []:
                relpath = path.relative_to(self.root).as_posix()
                try:
                    item = parse_item_file(path.read_text(encoding="utf-8"), relpath)
                    if (item.parent_key, item.field) != (key, field):
                        raise BundleError(f"the item belongs to {item.parent_key} / {item.field}, not here")
                    canonical = canonical_json(item_model.model_validate_json(item.value).model_dump(mode="json"))
                except (BundleError, ValidationError) as error:
                    raise BundleError(f"{relpath}: {error}") from error
                if sha256_hex(canonical) != item.hashcode:
                    raise BundleError(f"{relpath}: the stored JSON does not match its hashcode; the file was edited outside the system")
                rows.append(item.model_copy(update={"value": canonical}))
            found[field] = sorted(rows, key=lambda r: (r.position, r.relpath))
        return found

    def _checked(self, record: FactRecord, key: str) -> FactRecord:
        """`record` once the object assembled from the parent and its items validates against the entity model and hashes to the stored hashcode, else BundleError."""
        entity, key_errors = check_key(record.key)
        if key_errors:
            raise BundleError(f"{record.key}: {key_errors[0].message}")
        model = FACT_SPECS[entity]["model"]
        try:
            data = json.loads(record.value)
            split = split_fields(model)
            if split:
                for field, items in self._items_of(record.key, split).items():
                    if field not in data and items:
                        data[field] = [json.loads(item.value) for item in items]
            value = canonical_json(model.model_validate_json(json.dumps(data)).model_dump(mode="json"))
        except ValidationError as error:
            raise BundleError(f"{record.key}: the stored JSON no longer validates against {model.__name__} ({error.error_count()} errors)") from error
        if sha256_hex(value) != record.hashcode:
            raise BundleError(f"{record.key}: the stored JSON does not match its hashcode; the file was edited outside the system")
        return record.model_copy(update={"value": value})
