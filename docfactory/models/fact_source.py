from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class FactSource(DocFactoryModel):
    """One material a knowledge fact was derived from (an OKF sources[] entry), so a reader can trace the fact back to its original file."""

    resource: str = doc_field(
        description="Where the original is: the DocStore path with forward slashes, or an external URI, e.g. ReadmeForge/ReadmeForge SRS v0.3.pdf. Must not be empty.",
        question="Which file or URI did this fact come from?",
        min_length=1,
    )
    id: str | None = doc_field(
        default=None,
        description="Short stable label for the source, e.g. srs. None when no label is needed.",
        question="What short label identifies this source?",
    )
    title: str | None = doc_field(
        default=None,
        description="Human-readable title of the source, e.g. Software Requirements Specification v0.3. None when unknown.",
        question="What is the title of this source?",
    )
    last_modified: str | None = doc_field(
        default=None,
        description="When the source was last modified, ISO 8601 datetime with explicit UTC offset, e.g. 2026-06-30T14:00:00Z (the DocStore Timestamp of the file). None when unknown.",
        question="When was this source last modified?",
        pattern="^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$",
    )
