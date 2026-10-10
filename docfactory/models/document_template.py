from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.template_section import TemplateSection


class DocumentTemplate(DocFactoryModel):
    """A configuration-based document template: the validated form of one YAML file under configrender/templates/. It replaces the per-type document model, its sections and its saver: sections of fields bound to fact fields, in order."""

    doc_type: str = doc_field(
        description="The short document type, e.g. 'SRS'. It is the file name of the template and part of the stored keys and output file names.",
        question="What is the short name of this document type?",
        pattern=r"^[A-Za-z][A-Za-z0-9]*$",
    )
    name: str = doc_field(
        description="The full document name used in the document title, e.g. 'Software Requirements Specification'.",
        question="What is the full name of this document?",
        min_length=1,
    )
    sections: list[TemplateSection] = doc_field(
        description="The sections in document order. A good template has at least one section.",
        question="Which sections should this document have?",
        min_length=1,
    )
