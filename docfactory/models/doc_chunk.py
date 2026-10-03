from pydantic import field_validator

from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class DocChunk(DocFactoryModel):
    """One chunk of an original document, produced deterministically by ingestion: one section (or a part of a long section), never splitting a section or a table row. Later each chunk is tagged with the knowledge entities it informs."""

    chunk_no: int = doc_field(
        description="Position of the chunk in the document, starting at 1, e.g. 12.",
        question="What is the position of this chunk in the document (1 for the first)?",
    )
    heading: str = doc_field(
        description="Heading trail of the section, outermost first, joined with ' > ', e.g. '3. System Features > 3.1. User Management'. 'Front matter' for text before the first heading; a long section split into parts gets ' (part 2)' appended.",
        question="What is the heading trail of the section this chunk belongs to?",
        min_length=1,
    )
    page_from: int | None = doc_field(
        default=None,
        description="First page of the chunk for paged formats (PDF), e.g. 13; None for Word, HTML and text. Must be 1 or more when set.",
        question="On which page does this chunk start (paged formats only)?",
    )
    page_to: int | None = doc_field(
        default=None,
        description="Last page of the chunk for paged formats (PDF), e.g. 14; None for Word, HTML and text. Must be 1 or more when set.",
        question="On which page does this chunk end (paged formats only)?",
    )
    text: str = doc_field(
        description="The chunk's text: paragraphs as lines, table rows as cells joined with ' | ', e.g. 'FR-01. | The system SHALL provide a self-registration process.'",
        question="What is the text of this chunk?",
        min_length=1,
    )
    text_hash: str = doc_field(
        description="SHA-256 hex of text, 64 lower-case hex characters, e.g. 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'. Used to see which chunks changed between two versions of a file.",
        question="What is the SHA-256 hex of the chunk text?",
        pattern="^[0-9a-f]{64}$",
    )

    @field_validator("chunk_no", "page_from", "page_to")
    @classmethod
    def _at_least_one(cls, value: int | None) -> int | None:
        """Positions and page numbers count from 1."""
        if value is not None and value < 1:
            raise ValueError("must be 1 or more")
        return value
