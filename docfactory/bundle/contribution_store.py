from pathlib import Path

from docfactory import clock
from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_log import append_entry, append_log
from docfactory.bundle.contribution_file_parse import parse_contribution_file
from docfactory.bundle.contribution_file_render import render_contribution_file
from docfactory.bundle.file_io import put_text
from docfactory.bundle.paths import SOURCES_DIR, SUFFIX, bundle_root, contribution_relpath, is_entity_resource
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.fact_contribution import FactContribution


class ContributionStore:
    """What each ingested original contributed to each fact: one contribution concept per (original, entity),
    `<scope>/sources/<file name>/<Entity>.md`. A fact extracted from documents is the deterministic merge of its contributions, so
    re-extracting one file replaces only that file's contribution. Written only by the extraction pipeline; the fact files stay the truth.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else bundle_root()

    def get(self, key: str, resource: str) -> FactContribution | None:
        """The contribution of `resource` to the fact `key`, or None. BundleError when the file cannot be trusted."""
        path = self.root / contribution_relpath(key, resource)
        return self._parse(path) if path.is_file() else None

    def list(self, key: str | None = None, resource: str | None = None) -> list[FactContribution]:
        """Contributions ordered by fact key and resource; filtered by fact key and/or contributing resource."""
        records = [self._parse(path) for path in self._paths(key, resource)]
        records = [r for r in records if (key is None or r.fact_key == key) and (resource is None or r.resource == resource)]
        return sorted(records, key=lambda r: (r.fact_key, r.resource))

    def save(self, key: str, resource: str, value: dict, chunks_hash: str | None, description: str | None, generated_by: str,
             timestamp: str) -> FactContribution:
        """Store `value` (the partial fact this file states) as the contribution of `resource` to `key` and return it."""
        text = canonical_json(value)
        record = FactContribution(fact_key=key, resource=resource, value_json=text, hashcode=sha256_hex(text), chunks_hash=chunks_hash,
                                  description=description, generated_by=generated_by, timestamp=timestamp)
        relpath = contribution_relpath(key, resource)
        before = self.get(key, resource)
        put_text(self.root / relpath, render_contribution_file(record))
        if before is None or before.hashcode != record.hashcode:
            append_entry(self.root, timestamp[:10], f"* **{'Creation' if before is None else 'Update'}**: [{key} from {resource}](/{relpath}) by {generated_by}")
        return record

    def remove(self, key: str, resource: str) -> None:
        """Remove what `resource` contributed to the fact `key`, if anything (an emptied folder goes too)."""
        relpath = contribution_relpath(key, resource)
        path = self.root / relpath
        if not path.is_file():
            return
        path.unlink()
        if not any(path.parent.iterdir()):
            path.parent.rmdir()
        append_entry(self.root, clock.now_iso()[:10], f"* **Deprecation**: removed the contribution of {resource} to {key} (/{relpath})")

    def _paths(self, key: str | None, resource: str | None) -> list[Path]:
        if not self.root.is_dir():
            return []
        if key is not None and resource is not None:
            path = self.root / contribution_relpath(key, resource)
            return [path] if path.is_file() else []
        scope, entity = (key.split(".")[0], key.split(".")[-1]) if key else ("*", "*")
        if resource is None:
            name = "*"
        elif is_entity_resource(resource):
            name = resource.replace("/", "~")
        else:
            name = resource.rsplit("/", 1)[-1] if "/" in resource else resource
        return sorted(p for p in self.root.glob(f"{scope}/{SOURCES_DIR}/{name}/{entity}{SUFFIX}") if p.is_file())

    def _parse(self, path: Path) -> FactContribution:
        try:
            return parse_contribution_file(path.read_text(encoding="utf-8"))
        except BundleError as error:
            raise BundleError(f"{path.relative_to(self.root).as_posix()}: {error}") from error
