from docfactory.entitymodels.items.relation_kind import RelationKind
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class Relation(DocFactoryModel):
    """One relationship an item states about another item, in the document's own words: for example that FR-12 depends on FR-03. It becomes an edge of the relationship graph. One relation per target."""

    target: str = doc_field(
        description="Identifier of the other item exactly as the document writes it, e.g. 'FR-03' or 'Payment service'. It must appear in the text the relation is taken from.",
        question="Which other item does this item relate to?",
        min_length=1,
    )
    kind: RelationKind = doc_field(
        description="How the item relates to the target: depends_on, implements, refines, integrates_with, monitors, conflicts_with or relates_to, e.g. depends_on. Use relates_to only when no other kind fits.",
        question="How does this item relate to the other item?",
    )
    evidence: str = doc_field(
        default="",
        description="The words of the document that state the relation, short, e.g. 'requires the user to be logged in (FR-03)'. Empty when the identifier alone states it.",
        question="Which words of the document state this relation?",
    )
