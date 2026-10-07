from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class FactQuestion(DocFactoryModel):
    """One open question of a stored knowledge fact: a scored field still at its default, with the question and the default from the field's model definition. Written to knowledgefacts/<scope>/<Entity>.missing.md."""

    path: str = doc_field(
        description="Where the unanswered field is in the fact: field names joined by dots, with [] for the fields of list items, e.g. requirements[].acceptance_criteria.",
        question="Which field of the fact is unanswered?",
        min_length=1,
    )
    question: str = doc_field(
        description="The field's question from its model definition (its description when it declares no question), e.g. How do we know this requirement is met?",
        question="What question does the field ask?",
        min_length=1,
    )
    default_assumed: str = doc_field(
        description="The field's default from its model definition in words, which is what is assumed until someone answers, e.g. empty text, empty list, none or no.",
        question="What is assumed while the field is unanswered?",
        min_length=1,
    )
    missing_in: int | None = doc_field(
        default=None,
        description="For a field of list items: how many of the items still hold the default, e.g. 165. None for a field that is not inside a list.",
        question="In how many items is the field unanswered?",
    )
    item_count: int | None = doc_field(
        default=None,
        description="For a field of list items: how many items the list holds, e.g. 186. None for a field that is not inside a list.",
        question="How many items does the list hold?",
    )

