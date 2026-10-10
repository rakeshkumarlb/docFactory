from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.template_field import TemplateField


class TemplateSection(DocFactoryModel):
    """One section (a `##` heading and its fields) of a configuration-based document template."""

    id: str = doc_field(
        description="The section's identifier in snake_case, e.g. 'functional_requirements'. It names the section in gaps ('functional_requirements.requirements') and in the revision history, so it is unique within the template.",
        question="What is the identifier of this section?",
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    title: str = doc_field(
        description="The section heading exactly as it should appear, e.g. 'Functional Requirements'.",
        question="What is the heading of this section?",
        min_length=1,
    )
    fields: list[TemplateField] = doc_field(
        description="The section's fields in document order, each bound to a fact field. A good section has at least one field.",
        question="Which fact fields should this section show?",
        min_length=1,
    )
