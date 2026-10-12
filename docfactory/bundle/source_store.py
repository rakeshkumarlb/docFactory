from pathlib import Path

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.bundle_log import append_log
from docfactory.bundle.file_io import put_text
from docfactory.bundle.paths import RESERVED_FILES, SOURCES_DIR, SUFFIX, bundle_root, resolve_in, source_relpath
from docfactory.bundle.source_file_parse import parse_source_file
from docfactory.bundle.source_file_render import INGESTION_ACTOR, render_source_file
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.doc_chunk import DocChunk
from docfactory.models.source_chunk import SourceChunk
from docfactory.models.source_record import SourceRecord


class SourceStore:
    """The Source concepts of the bundle: one file per ingested original, `<scope>/sources/<file name>.md`.

    A Source holds the original's hash, version, chunk outline and entity tags (no chunk text). The ingestion pipeline writes it last, so
    its presence means the original is stored and tagged. The originals themselves sit in `<scope>/references/`.
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else bundle_root()

    def original(self, resource: str) -> Path:
        """The absolute path of the original `resource` (ValueError when it would leave the bundle)."""
        return resolve_in(self.root, resource)

    def read(self, resource: str) -> SourceRecord | None:
        """The Source of the original `resource` ('<scope>/references/<name>'), or None. BundleError when the file is not a Source."""
        path = self.root / source_relpath(resource)
        if not path.is_file():
            return None
        return self._parse(path)

    def list(self, scope: str | None = None) -> list[SourceRecord]:
        """Every Source ordered by path; with `scope`, only that scope folder's."""
        pattern = f"{scope}/{SOURCES_DIR}/*{SUFFIX}" if scope else f"*/{SOURCES_DIR}/*{SUFFIX}"
        paths = [p for p in self.root.glob(pattern) if p.is_file() and p.name not in RESERVED_FILES] if self.root.is_dir() else []
        return sorted((self._parse(p) for p in paths), key=lambda record: record.path)

    def find(self, file_name: str | None = None, hashcode: str | None = None) -> list[SourceRecord]:
        """The Sources whose original has the file name `file_name` and/or the hash `hashcode`, ordered by path."""
        return [r for r in self.list()
                if (file_name is None or r.path.rsplit("/", 1)[-1] == file_name) and (hashcode is None or r.hashcode == hashcode)]

    def write(self, resource: str, hashcode: str, timestamp: str, chunks: list[DocChunk], tags: list[ChunkTag], author: str | None = None) -> tuple[int, SourceRecord | None]:
        """Record the original `resource` with its chunk outline and tags, replacing any earlier ones. Returns (version, the record before).

        No earlier Source: version 1. Same hash: the version stays (a repair or a re-tag). Another hash: version + 1.
        `author` is what the file names in its properties; a re-tag of the same file (author None) keeps the stored one.
        """
        before = self.read(resource)
        version = 1 if before is None else before.version if before.hashcode == hashcode else before.version + 1
        record = SourceRecord(
            path=resource, hashcode=hashcode, version=version, timestamp=timestamp,
            author=author if author is not None else before.author if before is not None and before.hashcode == hashcode else None,
            chunks=[SourceChunk(chunk_no=c.chunk_no, heading=c.heading, text_hash=c.text_hash) for c in chunks], tags=tags,
        )
        put_text(self.root / source_relpath(resource), render_source_file(record))
        if before is None or before.version != version:
            append_log(self.root, timestamp[:10], "Creation" if before is None else "Update", resource, source_relpath(resource), version, INGESTION_ACTOR)
        return version, before

    def _parse(self, path: Path) -> SourceRecord:
        try:
            return parse_source_file(path.read_text(encoding="utf-8"))
        except BundleError as error:
            raise BundleError(f"{path.relative_to(self.root).as_posix()}: {error}") from error
