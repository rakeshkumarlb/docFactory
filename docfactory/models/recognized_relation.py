from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class RecognizedRelation(DocFactoryModel):
    """One relationship a recognition call found between two entities of a document, named by a verb phrase in the document's terms (e.g. Matching Engine 'depends on' Search Index). Recognition output; becomes a link of the entity graph."""

    source: str = doc_field(
        description="Name, alias or entity id of the entity the relationship is stated about, e.g. 'Matching Engine'.",
        question="Which entity is the relationship about?",
        min_length=1,
    )
    target: str = doc_field(
        description="Name, alias or entity id of the related entity, e.g. 'Search Index'.",
        question="Which entity is it related to?",
        min_length=1,
    )
    relation: str = doc_field(
        description="Verb phrase naming the relationship as the document states it, e.g. 'depends on', 'is owned by', 'is hosted on', 'is handled by runbook'.",
        question="How are the two entities related?",
        min_length=1,
    )
    kind: str = doc_field(
        default='',
        description="The closest standard kind, one of depends_on, implements, refines, integrates_with, monitors, conflicts_with, relates_to, e.g. 'depends_on'. Empty when none fits better than the verb phrase.",
        question="Which standard kind of relationship is it?",
    )
    chunks: list[int] = doc_field(
        default_factory=list,
        description="Numbers of the window's chunks that state the relationship, e.g. [14].",
        question="Which chunks state this relationship?",
    )
