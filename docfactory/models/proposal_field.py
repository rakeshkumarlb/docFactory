from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.proposal_field_type import ProposalFieldType


class ProposalField(DocFactoryModel):
    """One field of a proposed entity type (or of its item type): its name, kind and the description and question that make it usable by an LLM."""

    name: str = doc_field(
        description="Field name in snake_case, e.g. 'risk_owner'. Unique within its type.",
        question="What is the field called (snake_case)?",
        pattern="^[a-z][a-z0-9_]*$",
    )
    type: ProposalFieldType = doc_field(
        default=ProposalFieldType.TEXT,
        description="Kind of the field: 'str', 'list[str]', 'int | None' or 'bool', e.g. 'str'. The identifying first field of an item type must be 'str'.",
        question="Which kind of value does this field hold?",
    )
    description: str = doc_field(
        description="What the field means and what a good value looks like, written for an LLM and containing an example introduced by 'e.g.', e.g. 'Role or team that owns the risk, e.g. Product owner.'",
        question="What does this field mean, and what does a good value look like?",
        min_length=20,
    )
    question: str = doc_field(
        description="The question to ask when the field is missing, ending with a question mark, e.g. 'Who owns this risk?'",
        question="Which question asks for this field?",
        pattern="\\?$",
    )
