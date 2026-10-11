from docfactory.models.chunk_tag import ChunkTag
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.source_chunk import SourceChunk


class SourceRecord(DocFactoryModel):
    """What the bundle remembers about one ingested original (its Source concept): where the original is, its hash and version, its chunk outline and the entity tags on its chunks. Everything else (the chunk text) is derived from the original."""

    path: str = doc_field(
        description="Bundle-relative path of the original with forward slashes, '<scope>/references/<file name>', e.g. 'AI-Driven-Job-Matching-Platform/references/Annex-A SRS.pdf'.",
        question="Where in the bundle is the original?",
        min_length=1,
    )
    hashcode: str = doc_field(
        description="SHA-256 hex of the original file's bytes, 64 lower-case hex characters.",
        question="What is the hash of the original file?",
        pattern="^[0-9a-f]{64}$",
    )
    version: int = doc_field(
        description="Version of the original, 1 for the first ingestion and +1 for every changed revision, e.g. 2.",
        question="Which version of the original is this?",
        ge=1,
    )
    timestamp: str = doc_field(
        description="When the original was ingested, ISO 8601 datetime with explicit UTC offset, e.g. 2026-10-03T12:00:00+00:00.",
        question="When was the original ingested?",
        min_length=1,
    )
    chunks: list[SourceChunk] = doc_field(
        default_factory=list,
        description="The chunk outline of the original in order (number, heading, text hash), e.g. 76 entries for a 50-page SRS.",
        question="What is the chunk outline of the original?",
        scored=False,
    )
    tags: list[ChunkTag] = doc_field(
        default_factory=list,
        description="The entity tags on the chunks, set by the rules or by the LLM fallback, e.g. chunk 15 tagged FunctionalRequirements by 'rule'. Empty when nothing was tagged.",
        question="Which entities are the chunks tagged with?",
        scored=False,
    )
