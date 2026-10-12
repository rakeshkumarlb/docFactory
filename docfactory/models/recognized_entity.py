from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class RecognizedEntity(DocFactoryModel):
    """One entity a recognition call found in a window of a document: a thing the document discusses (a component, an environment, a runbook, a decision, ...), with its canonical name, its type and the chunks that discuss it. Recognition output, checked by code before it is stored; holds no fact values."""

    name: str = doc_field(
        description="Canonical display name of the entity as the document most often states it, e.g. 'Matching Engine' or 'Production'. Never a generic phrase such as 'the platform'.",
        question="What is the canonical name of this entity?",
        min_length=1,
    )
    type: str = doc_field(
        description="Entity type from the recognition vocabulary, e.g. 'Component' or 'Environment', or 'proposed:<PascalName>' (e.g. 'proposed:Certificate') when no vocabulary type fits.",
        question="Which entity type is this?",
        min_length=1,
    )
    aliases: list[str] = doc_field(
        default_factory=list,
        description="Other names or abbreviations the document uses for the same entity, e.g. ['Keycloak'] for 'Identity Service'. Empty when it has no other name.",
        question="Which other names does the document use for this entity?",
    )
    same_as: str | None = doc_field(
        default=None,
        description="Entity id of an EXISTING entity from the catalog this one is the same as, e.g. 'Component/matching-engine'. None when it is new or matched by name.",
        question="Which existing entity is this the same as?",
    )
    summary: str = doc_field(
        default='',
        description="One sentence saying what the entity is, in the document's terms, e.g. 'Ranks job seekers against vacancies using skills and embeddings.' Empty when the window says too little.",
        question="What is this entity, in one sentence?",
    )
    chunks: list[int] = doc_field(
        default_factory=list,
        description="Numbers of the window's chunks that discuss this entity, e.g. [12, 13]. Every number must be a chunk of the window.",
        question="Which chunks discuss this entity?",
    )
    reason: str = doc_field(
        default='',
        description="Only for a proposed type: why no vocabulary type fits, e.g. 'A TLS certificate is neither a component nor a data store.' Empty for vocabulary types.",
        question="Why does no vocabulary type fit this entity?",
    )
