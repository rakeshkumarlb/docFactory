from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class GraphEdge(DocFactoryModel):
    """One directed relationship between two concepts of the bundle (OKF links are untyped edges whose kind the prose states; here the kind is explicit). Derived on every run, never stored."""

    source: str = doc_field(
        description="Node id (bundle path starting with '/') the relationship starts at, e.g. '/Acme/FunctionalRequirements/requirements/FR-12.md'.",
        question="Where does the relationship start?",
        min_length=1,
    )
    target: str = doc_field(
        description="Node id the relationship points to, e.g. '/Acme/FunctionalRequirements/requirements/FR-03.md'; when it is unresolved, the identifier as the document wrote it, e.g. 'FR-99'.",
        question="Where does the relationship point to?",
        min_length=1,
    )
    kind: str = doc_field(
        description="What the relationship is: 'part_of' or 'derived_from' (structure), 'references' (the text names the other item), or a stated kind such as 'depends_on', 'implements', 'refines', 'integrates_with', 'monitors', 'conflicts_with' or 'relates_to'.",
        question="What kind of relationship is this?",
        min_length=1,
    )
    origin: str = doc_field(
        description="How the edge was found: 'structural' (from the bundle's layout), 'mentioned' (an identifier in the item's text) or 'stated' (a relation the extraction took from the document).",
        question="How was this edge found?",
        pattern="^(structural|mentioned|stated)$",
    )
    evidence: str = doc_field(
        default="",
        description="The words that state the relation, for stated edges, e.g. 'requires the user to be logged in (FR-03)'. Empty otherwise.",
        question="Which words state this relationship?",
    )
    resolved: bool = doc_field(
        default=True,
        description="True when the target is a concept of the bundle; false for a broken link (the target is named but not stored, which OKF allows).",
        question="Does the target exist in the bundle?",
    )
