from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.chunk_topic import ChunkTopic
from docfactory.models.recognized_entity import RecognizedEntity
from docfactory.models.recognized_relation import RecognizedRelation


class WindowRecognition(DocFactoryModel):
    """The accepted recognition of one window of a document: the window's chunks and hash and what the call found in it (entities, relationships, chunk topics). Kept per window so an unchanged window is never sent to the model again."""

    window_hash: str = doc_field(
        description="SHA-256 hex of the window's chunk headings and texts, 64 lower-case hex characters, e.g. the chunks_hash of its chunks. Unchanged hash = no new call.",
        question="What is the hash of this window's chunks?",
        pattern="^[0-9a-f]{64}$",
    )
    chunk_nos: list[int] = doc_field(
        default_factory=list,
        description="Numbers of the chunks in the window, in document order, e.g. [3, 4, 5].",
        question="Which chunks make up this window?",
    )
    entities: list[RecognizedEntity] = doc_field(
        default_factory=list,
        description="The entities the window discusses, one entry each, e.g. one entity named 'Matching Engine'. Empty when it discusses none.",
        question="Which entities does this window discuss?",
    )
    relations: list[RecognizedRelation] = doc_field(
        default_factory=list,
        description="The relationships the window states between entities, e.g. Matching Engine depends on Search Index. Empty when it states none.",
        question="Which relationships does this window state?",
    )
    topics: list[ChunkTopic] = doc_field(
        default_factory=list,
        description="Per chunk, the knowledge facts it informs, e.g. chunk 3 informs Deployment. Chunks that inform no fact may be left out.",
        question="Which knowledge facts does each chunk inform?",
    )
