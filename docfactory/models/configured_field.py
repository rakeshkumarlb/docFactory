from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ConfiguredField(DocFactoryModel):
    """One field of a configuration-based document body: the value copied from a fact field, with the binding and rendering it came with. Only `value` is scored, so the body's completeness is the share of bound fields that were answered."""

    binding: str = doc_field(
        description="The fact field this value was copied from, '<Entity>.<field>', e.g. 'ApplicationOverview.purpose'.",
        question="Which fact field does this value come from?",
        min_length=1,
        scored=False,
    )
    label: str = doc_field(
        description="The label shown in front of the value, e.g. 'Purpose'.",
        question="Which label does this field have?",
        min_length=1,
        scored=False,
    )
    render_as: str = doc_field(
        default='list',
        description="How a list value is rendered: 'list', 'numbered' or 'table'.",
        question="How should this value be rendered?",
        scored=False,
        pattern=r"^(list|numbered|table)$",
    )
    status: str = doc_field(
        default='missing',
        description="'answered' when the fact field holds an answer, 'missing' when the fact is absent or the field is still at its default.",
        question="Was this field answered by the facts?",
        scored=False,
        pattern=r"^(answered|missing)$",
    )
    value: str = doc_field(
        default='',
        description="The fact field's value as canonical JSON text, e.g. '\"Keeps READMEs current\"' or '[{\"id\":\"FR-01\"}]'. Empty when the field is missing; never invented.",
        question="What does the fact say for this field?",
    )
