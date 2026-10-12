from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class NoteDraft(DocFactoryModel):
    """What the discovery call proposes as one note: a passage of the chunks it was shown that fits no knowledge entity. Code turns an accepted draft into a NoteEntry of the Note fact and sets its source chunks from `chunks`."""

    title: str = doc_field(
        description="Short title of the note in the document's own words, e.g. 'Document revision history' or 'Open issues list'.",
        question="What is the title of this note?",
        min_length=1,
    )
    summary: str = doc_field(
        default="",
        description="One or two sentences saying what the passage holds, using only what the chunks state, e.g. 'Lists the open issues and who owns them.'",
        question="What does the passage say, in one or two sentences?",
    )
    statements: list[str] = doc_field(
        default_factory=list,
        description="The individual statements of the passage, copied or closely paraphrased from the chunks, e.g. ['Open issue 1: the payment provider is not chosen yet.'].",
        question="Which statements does the passage contain?",
    )
    kind: str = doc_field(
        default="",
        description="What sort of passage it is, in a word or two, e.g. 'cover page', 'appendix', 'glossary' or 'issues list'.",
        question="What sort of passage is this?",
    )
    chunks: list[int] = doc_field(
        description="The numbers of the chunks the note is written from, taken from the '[chunk N]' markers, e.g. [75]. At least one.",
        question="Which chunk numbers is this note written from?",
        min_length=1,
    )
