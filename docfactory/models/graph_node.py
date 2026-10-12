from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class GraphNode(DocFactoryModel):
    """One concept of the bundle as a node of the relationship graph: a fact, one item of a fact's list, or a Source. Derived on every run from the concept files, never stored."""

    id: str = doc_field(
        description="Bundle-relative path of the concept file starting with '/', e.g. '/Acme/FunctionalRequirements/requirements/FR-01.md'. Unique.",
        question="Which concept file is this node?",
        min_length=1,
    )
    type: str = doc_field(
        description="The OKF type of the concept in words, e.g. 'Requirement', 'Functional Requirements' or 'Source'.",
        question="What kind of concept is this node?",
        min_length=1,
    )
    title: str = doc_field(
        description="Display name of the concept, e.g. 'FR-01' for an item or 'Acme functional requirements' for a fact.",
        question="What is the display name of the node?",
        min_length=1,
    )
    identifier: str = doc_field(
        default="",
        description="For an item, its identifier as the document writes it, e.g. 'FR-01'; empty for facts and Sources. Relations and mentions are resolved against it.",
        question="What identifies the item in the documents?",
    )
