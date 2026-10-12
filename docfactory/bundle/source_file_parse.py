"""Reads a Source concept file back into a SourceRecord."""
from pydantic import ValidationError

from docfactory.bundle.bundle_error import BundleError
from docfactory.bundle.frontmatter_yaml import load_frontmatter
from docfactory.bundle.source_file_render import SOURCE_TYPE
from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.source_chunk import SourceChunk
from docfactory.models.source_record import SourceRecord

_OPEN = "---\n"
_CLOSE = "\n---\n"


def parse_source_file(text: str) -> SourceRecord:
    """The record stored in `text`; BundleError when the file is not a Source concept."""
    try:
        if not text.startswith(_OPEN) or _CLOSE not in text:
            raise ValueError("the file has no frontmatter block")
        meta = load_frontmatter(text[len(_OPEN):text.index(_CLOSE) + 1])
        if meta.get("type") != SOURCE_TYPE:
            raise ValueError(f"type is {meta.get('type')!r}, not {SOURCE_TYPE!r}")
        return SourceRecord(
            path=meta["resource"], hashcode=meta["hashcode"], version=meta["version"], timestamp=meta["generated"]["at"], author=meta.get("author"),
            chunks=[SourceChunk(chunk_no=c["chunk"], heading=c["heading"], text_hash=c["hash"]) for c in meta.get("chunks") or []],
            tags=[ChunkTag(chunk_no=t["chunk"], entity=t["entity"], origin=t["origin"], score=t["score"], evidence=t["evidence"])
                  for t in meta.get("chunk_tags") or []],
        )
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise BundleError(f"not a readable Source concept: {error}") from error
