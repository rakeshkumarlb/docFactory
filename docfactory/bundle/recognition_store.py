from pathlib import Path

from docfactory import clock
from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_log import append_entry
from docfactory.bundle.file_io import put_text
from docfactory.bundle.paths import RECOGNITION_DIR, SUFFIX, bundle_root, recognition_relpath
from docfactory.bundle.recognition_file_parse import parse_recognition_file
from docfactory.bundle.recognition_file_render import render_recognition_file
from docfactory.canonical import canonical_json, sha256_hex
from docfactory.models.file_recognition import FileRecognition
from docfactory.models.window_recognition import WindowRecognition


class RecognitionStore:
    """What recognition found in each ingested original: one recognition concept per original, `<scope>/recognition/<file name>.md`.
    The entity graph of a scope is the deterministic merge of its recognitions, so re-recognizing one file replaces only that file's share.
    Written only by the recognition pipeline.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else bundle_root()

    def get(self, resource: str) -> FileRecognition | None:
        """The recognition of `resource`, or None. BundleError when the file cannot be trusted."""
        path = self.root / recognition_relpath(resource)
        return self._parse(path) if path.is_file() else None

    def list(self, scope: str | None = None) -> list[FileRecognition]:
        """The recognitions of a scope (or of every scope), ordered by resource."""
        if not self.root.is_dir():
            return []
        paths = sorted(p for p in self.root.glob(f"{scope or '*'}/{RECOGNITION_DIR}/*{SUFFIX}") if p.is_file())
        return sorted((self._parse(p) for p in paths), key=lambda r: r.resource)

    def save(self, resource: str, windows: list[WindowRecognition], generated_by: str, timestamp: str) -> FileRecognition:
        """Store `windows` as the recognition of `resource` (replacing an earlier one) and return the record."""
        data = [w.model_dump(mode="json") for w in windows]
        record = FileRecognition(resource=resource, windows=windows, hashcode=sha256_hex(canonical_json(data)), generated_by=generated_by, timestamp=timestamp)
        relpath = recognition_relpath(resource)
        before = self.get(resource)
        put_text(self.root / relpath, render_recognition_file(record))
        if before is None or before.hashcode != record.hashcode:
            append_entry(self.root, timestamp[:10], f"* **{'Creation' if before is None else 'Update'}**: [recognition of {resource}](/{relpath}) by {generated_by}")
        return record

    def remove(self, resource: str) -> None:
        """Remove the recognition of `resource`, if any."""
        relpath = recognition_relpath(resource)
        path = self.root / relpath
        if path.is_file():
            path.unlink()
            append_entry(self.root, clock.now_iso()[:10], f"* **Deprecation**: removed the recognition of {resource} (/{relpath})")

    def _parse(self, path: Path) -> FileRecognition:
        try:
            return parse_recognition_file(path.read_text(encoding="utf-8"))
        except BundleError as error:
            raise BundleError(f"{path.relative_to(self.root).as_posix()}: {error}") from error
