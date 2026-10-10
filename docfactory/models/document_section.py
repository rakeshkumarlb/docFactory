from docfactory.models.document_field import DocumentField
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class DocumentSection(DocFactoryModel):
    """One section of a document body: its heading and its fields, built from the template and the facts."""

    id: str = doc_field(
        description="The section identifier from the template, e.g. 'functional_requirements'.",
        question="Which template section is this?",
        min_length=1,
        scored=False,
    )
    title: str = doc_field(
        description="The section heading from the template, e.g. 'Functional Requirements'.",
        question="What is the heading of this section?",
        min_length=1,
        scored=False,
    )
    fields: list[DocumentField] = doc_field(
        default_factory=list,
        description="The section's fields in template order, each with the value copied from its fact.",
        question="Which fields does this section hold?",
    )
