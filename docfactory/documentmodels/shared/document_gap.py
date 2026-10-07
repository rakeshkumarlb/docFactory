from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class DocumentGap(DocFactoryModel):
    """One numbered gap of a generated document: a document field no fact fills, or a bound fact field that is still unanswered. Built by code from the model metadata; the needs list cites gaps by number."""

    number: int = doc_field(
        description="The gap's number within the document's needs list, starting at 1 in template order, e.g. 3. Needs cite gaps by this number.",
        question="Which number does this gap have in the needs list?",
        ge=1,
        binding="caller",
    )
    field: str = doc_field(
        description="Dotted path of the document field that lacks a value, e.g. 'application_summary.business_criticality'. Fields of list items use [] for the list, e.g. 'functional_requirements.requirements[].acceptance_criteria'.",
        question="Which document field is missing a value?",
        min_length=1,
        binding="caller",
    )
    question: str = doc_field(
        description="The question to ask to get this value, copied from the missing field's own metadata, e.g. 'What is the primary business purpose of this application?'.",
        question="What question should be asked to obtain this value?",
        min_length=1,
        binding="caller",
    )
    expected_source: str = doc_field(
        description="The fact field that should supply this value, as '<Entity>.<field>', e.g. 'FunctionalRequirements.requirements'; for a field of list items the item path may follow, e.g. 'FunctionalRequirements.requirements[].acceptance_criteria'.",
        question="Which fact field should supply this value?",
        min_length=1,
        binding="caller",
    )
    missing_in: int | None = doc_field(
        default=None,
        description="For a field of list items, how many items lack it, e.g. 12. None for any other field.",
        question="For a field of list items, in how many items is it missing?",
        binding="caller",
    )
    item_count: int | None = doc_field(
        default=None,
        description="For a field of list items, how many items the list holds, e.g. 186. None for any other field.",
        question="For a field of list items, how many items does the list hold?",
        binding="caller",
    )
    example_items: list[str] = doc_field(
        default_factory=list,
        description="Up to 3 of the items lacking the field, each named by its mandatory fields joined by ' | ', e.g. 'FR-01 | Login | The system SHALL ...'. Empty outside lists.",
        question="Which items of the list lack this field?",
        max_length=3,
        binding="caller",
    )
