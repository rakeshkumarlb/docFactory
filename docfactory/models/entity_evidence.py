from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class EntityEvidence(DocFactoryModel):
    """One place in an ingested original that discusses an entity: the original and the chunk (re-derivable from the original). Lets extraction gather an entity's text deterministically and keeps every fact traceable to its source location."""

    resource: str = doc_field(
        description="Bundle path of the original, e.g. 'Acme/references/architecture.pdf'.",
        question="Which original discusses the entity?",
        min_length=1,
    )
    chunk_no: int = doc_field(
        description="Number of the chunk in that original, counting from 1, e.g. 12.",
        question="Which chunk discusses the entity?",
    )
    heading: str = doc_field(
        default='',
        description="Heading trail of the chunk, e.g. '4. Components > 4.2 Matching Engine'.",
        question="What is the heading trail of that chunk?",
    )
    text_hash: str = doc_field(
        default='',
        description="SHA-256 hex of the chunk text at recognition time, e.g. a 64-character hex string; a different hash means the chunk changed since.",
        question="What was the hash of the chunk text?",
    )
