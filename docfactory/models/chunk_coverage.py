from docfactory.models.coverage_status import CoverageStatus
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ChunkCoverage(DocFactoryModel):
    """Where the content of one chunk of an ingested original ended up: its status, the entities it is tagged with and, when the content is not in a fact, why. Derived data for the coverage report, never stored."""

    chunk_no: int = doc_field(
        description="Position of the chunk in the document, starting at 1, e.g. 12.",
        question="What is the position of this chunk in the document (1 for the first)?",
        ge=1,
    )
    heading: str = doc_field(
        description="Heading trail of the chunk's section, e.g. '3. System Features > 3.1. User Management'.",
        question="What is the heading trail of this chunk?",
        min_length=1,
    )
    chars: int = doc_field(
        default=0,
        description="Number of characters of the chunk's text, e.g. 1800. Shows how much content is at stake when the chunk is not in a fact.",
        question="How many characters does the chunk's text have?",
        ge=0,
    )
    status: CoverageStatus = doc_field(
        description="What became of the chunk: EXTRACTED, NOT_EXTRACTED, SKIPPED_SCOPE or UNMAPPED, e.g. UNMAPPED.",
        question="What became of this chunk?",
    )
    entities: list[str] = doc_field(
        default_factory=list,
        description="The entities the chunk is tagged with, sorted, e.g. ['Architecture', 'Slo']. Empty for an UNMAPPED chunk.",
        question="Which entities is this chunk tagged with?",
    )
    reason: str = doc_field(
        default="",
        description="Why the content is not in a fact, e.g. 'Slo is a shared fact (Shared.Slo); it is taken only from files in shared/' or 'no entity is tagged on this chunk'. Empty for an EXTRACTED chunk.",
        question="Why is the content of this chunk not in a fact?",
    )
