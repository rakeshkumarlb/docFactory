from pydantic import field_validator

from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ChunkTag(DocFactoryModel):
    """One entity tag on one chunk of an ingested document: the chunk informs this knowledge entity. Tags are set by deterministic rules from the ontology signals, or by the LLM fallback for chunks the rules could not tag."""

    chunk_no: int = doc_field(
        description="Number of the chunk the tag is on, counting from 1, e.g. 15.",
        question="Which chunk (1 for the first) does this tag belong to?",
    )
    entity: str = doc_field(
        description="Name of the knowledge entity model this chunk informs, e.g. FunctionalRequirements.",
        question="Which knowledge entity does this chunk inform?",
        min_length=1,
    )
    origin: str = doc_field(
        description="Who set the tag: 'rule' for the deterministic tagger, or 'llm/<model>' for the LLM fallback, e.g. 'rule' or 'llm/gemma4:31b'.",
        question="Who set this tag (rule or llm/<model>)?",
        min_length=1,
    )
    score: int = doc_field(
        default=0,
        description="The rule score that produced the tag (heading match, identifier match and keyword hits added up), e.g. 6; 0 for LLM tags.",
        question="What rule score produced this tag?",
    )
    evidence: str = doc_field(
        default="",
        description="What matched, for the report, e.g. \"heading 'functional requirements'; ids FR-01..FR-12\", or the LLM's short reason.",
        question="What evidence supports this tag?",
    )

    @field_validator("chunk_no")
    @classmethod
    def _at_least_one(cls, value: int) -> int:
        """Chunk numbers count from 1."""
        if value < 1:
            raise ValueError("must be 1 or more")
        return value
