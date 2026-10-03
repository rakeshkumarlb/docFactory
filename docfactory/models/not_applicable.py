from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class NotApplicable(DocFactoryModel):
    """A typed 'not applicable' answer: the question was considered and does not apply. It counts as answered, and is accepted only on fields declared na_allowed."""

    reason: str = doc_field(
        description="Why the question does not apply, in one sentence, e.g. 'The application is a batch job and has no web UI.' Never empty and never a placeholder such as 'n/a'.",
        question="Why is this not applicable?",
        min_length=1,
    )
