from pathlib import Path

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_log import append_log
from docfactory.bundle.entity_file_parse import parse_entity_file
from docfactory.bundle.entity_file_render import ENTITY_GENERATOR, render_entity_file
from docfactory.bundle.file_io import put_text
from docfactory.bundle.paths import ENTITIES_DIR, RESERVED_FILES, SUFFIX, bundle_root, entity_relpath
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.entity_record import EntityRecord

INDEX_FILE = "index.md"


class EntityStore:
    """The entity graph of each scope: one entity concept per recognized entity, `<scope>/entities/<Type>/<slug>.md`, plus a generated
    `<scope>/entities/index.md`. The graph is derived data (the merge of the scope's recognitions), so it is always written as a whole:
    changed entities get version + 1, unchanged ones are untouched, entities no longer recognized are removed. Written only by the
    recognition pipeline; a file whose JSON no longer matches its hash is refused on read.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else bundle_root()

    def list(self, scope: str) -> list[EntityRecord]:
        """The entities of `scope`, ordered by entity id."""
        return [record for record, _, _ in self._read_all(scope).values()]

    def get(self, scope: str, entity_id: str) -> EntityRecord | None:
        """One entity, or None."""
        path = self.root / entity_relpath(scope, entity_id)
        return self._parse(path)[0] if path.is_file() else None

    def write_all(self, scope: str, records: list[EntityRecord], timestamp: str) -> dict[str, list[str]]:
        """Make the entity graph of `scope` exactly `records`; returns the entity ids created, updated and removed."""
        before = self._read_all(scope)
        names = {r.entity_id: r.name for r in records}
        done: dict[str, list[str]] = {"created": [], "updated": [], "removed": []}
        for record in sorted(records, key=lambda r: r.entity_id):
            hashcode = sha256_hex(canonical_json(record.model_dump(mode="json")))
            old = before.get(record.entity_id)
            if old is not None and old[2] == hashcode:
                version = old[1]
            else:
                version = 1 if old is None else old[1] + 1
            relpath = entity_relpath(scope, record.entity_id)
            if old is not None and old[2] == hashcode:
                continue  # unchanged: the file (and its generated.at) is left as it is
            put_text(self.root / relpath, render_entity_file(record, version, hashcode, timestamp, names))
            done["created" if old is None else "updated"].append(record.entity_id)
            append_log(self.root, timestamp[:10], "Creation" if old is None else "Update", f"{scope} {record.type} {record.name}", relpath, version, ENTITY_GENERATOR)
        for entity_id in sorted(set(before) - set(names)):
            relpath = entity_relpath(scope, entity_id)
            (self.root / relpath).unlink()
            folder = (self.root / relpath).parent
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
            done["removed"].append(entity_id)
            append_log(self.root, timestamp[:10], "Deprecation", f"{scope} entity {entity_id}", relpath, before[entity_id][1], ENTITY_GENERATOR)
        put_text(self.root / scope / ENTITIES_DIR / INDEX_FILE, self._index(scope, records))
        return done

    def _index(self, scope: str, records: list[EntityRecord]) -> str:
        lines = [f"# {scope} entities"]
        current = None
        for record in sorted(records, key=lambda r: (r.type, r.name.lower())):
            if record.type != current:
                current = record.type
                lines += ["", f"## {current}", ""]
            entry = f"* [{record.name}](/{entity_relpath(scope, record.entity_id)})"
            lines.append(entry + (f" - {record.summary}" if record.summary else ""))
        return "\n".join(lines) + "\n"

    def _read_all(self, scope: str) -> dict[str, tuple[EntityRecord, int, str]]:
        folder = self.root / scope / ENTITIES_DIR
        if not folder.is_dir():
            return {}
        found = {}
        for path in sorted(p for p in folder.glob(f"*/*{SUFFIX}") if p.is_file() and p.name not in RESERVED_FILES):
            record, version, hashcode = self._parse(path)
            found[record.entity_id] = (record, version, hashcode)
        return dict(sorted(found.items()))

    def _parse(self, path: Path) -> tuple[EntityRecord, int, str]:
        try:
            return parse_entity_file(path.read_text(encoding="utf-8"))
        except BundleError as error:
            raise BundleError(f"{path.relative_to(self.root).as_posix()}: {error}") from error
