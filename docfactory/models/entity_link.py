from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class EntityLink(DocFactoryModel):
    """One relationship of an entity in the entity graph: the related entity, the verb phrase and the originals that state it (e.g. depends on Component/search-index, stated by the architecture document)."""

    target: str = doc_field(
        description="Entity id of the related entity, e.g. 'DataStore/search-index', or the plain name when it is not (yet) an entity of the graph.",
        question="Which entity is it related to?",
        min_length=1,
    )
    relation: str = doc_field(
        description="Verb phrase naming the relationship, e.g. 'depends on'.",
        question="How are the entities related?",
        min_length=1,
    )
    kind: str = doc_field(
        default='',
        description="Closest standard kind (depends_on, implements, refines, integrates_with, monitors, conflicts_with, relates_to), e.g. 'depends_on'; empty when none was given.",
        question="Which standard kind of relationship is it?",
    )
    resources: list[str] = doc_field(
        default_factory=list,
        description="Bundle paths of the originals that state the relationship, e.g. ['Acme/references/architecture.pdf'].",
        question="Which originals state this relationship?",
    )
