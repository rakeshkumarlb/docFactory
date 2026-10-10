from docfactory.models.document_section import DocumentSection
from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class DocumentBody(DocFactoryModel):
    """The body of a document (without document control and revision history): the template's sections filled from the facts. Stored in ConfiguredDocuments as `<App>.Configured.<DocType>`."""

    sections: list[DocumentSection] = doc_field(
        default_factory=list,
        description="The sections in template order, each with its fields. An empty list means nothing was built yet.",
        question="Which sections does the document have?",
    )
