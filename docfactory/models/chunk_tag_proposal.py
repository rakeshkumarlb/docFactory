from pydantic import field_validator

from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ChunkTagProposal(DocFactoryModel):
    """The LLM fallback's answer for one chunk of an ingested document that the deterministic tagger could not tag: which knowledge entities the chunk informs, and why. It is the item type of the submit_chunk_tags tool argument."""

    chunk_no: int = doc_field(
        description="Number of the chunk being tagged, counting from 1, exactly as given in the request, e.g. 39.",
        question="Which chunk (1 for the first) is this answer about?",
    )
    entities: list[str] = doc_field(
        default_factory=list,
        description="Knowledge entities this chunk informs, names copied exactly from the entity list in the request, e.g. ['Architecture']. An empty list means the chunk informs none of them (cover pages, appendices with diagrams, glossaries).",
        question="Which entities from the list does this chunk inform (empty if none)?",
    )
    reason: str = doc_field(
        description="One short sentence on why, quoting the words in the chunk that decided it, e.g. \"lists the external systems the platform exchanges data with ('REST APIs to the MoL database')\".",
        question="Why does this chunk inform these entities, or none (quote the deciding words)?",
        min_length=1,
    )

    @field_validator("chunk_no")
    @classmethod
    def _at_least_one(cls, value: int) -> int:
        """Chunk numbers count from 1."""
        if value < 1:
            raise ValueError("must be 1 or more")
        return value
