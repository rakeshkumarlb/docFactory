from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class SourceChunk(DocFactoryModel):
    """One chunk of an ingested original as the Source concept remembers it: its place, heading trail and text hash, never its text (the text is re-derived from the original, which chunks the same way every time)."""

    chunk_no: int = doc_field(
        description="Position of the chunk in the document, starting at 1, e.g. 12.",
        question="What is the position of this chunk in the document (1 for the first)?",
        ge=1,
    )
    heading: str = doc_field(
        description="Heading trail of the section, outermost first, joined with ' > ', e.g. '3. System Features > 3.1. User Management'.",
        question="What is the heading trail of the section this chunk belongs to?",
        min_length=1,
    )
    text_hash: str = doc_field(
        description="SHA-256 hex of the chunk text, 64 lower-case hex characters. Shows which chunks changed between two versions of a file and whether the original still chunks as it did at ingestion.",
        question="What is the SHA-256 hex of the chunk text?",
        pattern="^[0-9a-f]{64}$",
    )
