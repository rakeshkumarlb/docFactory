from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ChunkTopic(DocFactoryModel):
    """Which knowledge facts one chunk of a document informs, as decided by a recognition call (e.g. chunk 7 informs Deployment and BackupRecovery). Replaces keyword routing for the extraction of a fact's own fields."""

    chunk_no: int = doc_field(
        description="Number of the chunk, counting from 1, e.g. 7. Must be a chunk of the window.",
        question="Which chunk is this?",
    )
    facts: list[str] = doc_field(
        default_factory=list,
        description="Names of the knowledge facts the chunk gives information for, from the closed list of taggable facts, e.g. ['Deployment']. Empty when it informs none.",
        question="Which knowledge facts does this chunk inform?",
    )
