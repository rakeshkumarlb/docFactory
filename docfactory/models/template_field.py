from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class TemplateField(DocFactoryModel):
    """One field of a document template: which fact field fills it, how it is labelled and how it is rendered. The template is a YAML file; this is the validated form of one line of it."""

    binding: str = doc_field(
        description="The fact field that supplies this field, written '<Entity>.<field>', e.g. 'FunctionalRequirements.requirements' or 'Kpis.kpis'. The entity and the field must exist in the entity models; shared entities (Kpis, Slo) are read from their Shared fact.",
        question="Which '<Entity>.<field>' of the knowledge facts should fill this field?",
        pattern=r"^[A-Za-z][A-Za-z0-9]*\.[a-z][a-z0-9_]*$",
    )
    label: str = doc_field(
        default='',
        description="The label shown in front of the value, e.g. 'Out Of Scope'. Leave empty to use the source field's name in title case ('out_of_scope' becomes 'Out Of Scope').",
        question="Which label should this field have in the document?",
    )
    render_as: str = doc_field(
        default='list',
        description="How a list is rendered: 'list' (bullets, or numbered detail items for a list of models), 'numbered' (an ordered list of strings) or 'table' (one Markdown table for a list of models). It has no effect on a single value.",
        question="Should this list be rendered as a list, a numbered list or a table?",
        pattern=r"^(list|numbered|table)$",
    )
    question: str = doc_field(
        default='',
        description="The question asked when the fact field is missing, e.g. 'Which functional requirements does the application have?'. Leave empty to use the question of the entity field.",
        question="What should be asked when this field has no answer?",
    )
