from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class NoteEntry(DocFactoryModel):
    """One note: a piece of knowledge from an original document that fits no knowledge entity of the ontology (for example a cover page, an appendix or a remark), kept so that it is not lost."""

    title: str = doc_field(
        description="Short title of the note in the document's own words, e.g. 'Document revision history' or 'Open issues list'. Never empty.",
        question="What is the title of this note?",
        min_length=1,
    )
    summary: str = doc_field(
        default='',
        description="One or two sentences saying what the note holds, using only what the document states, e.g. 'Lists the open issues and who owns them.'",
        question="What does this note say, in one or two sentences?",
    )
    statements: list[str] = doc_field(
        default_factory=list,
        description="The individual statements of the note, each copied or closely paraphrased from the document, e.g. ['Open issue 1: the payment provider is not chosen yet.']. Empty when the summary says it all.",
        question="Which statements does this note contain?",
    )
    kind: str = doc_field(
        default='',
        description="What sort of passage the note comes from, in a word or two, e.g. 'cover page', 'appendix', 'glossary' or 'issues list'.",
        question="What sort of passage is this note (cover page, appendix, glossary, ...)?",
    )
    source_chunks: list[str] = doc_field(
        default_factory=list,
        description="Where the note comes from, one entry per chunk as '<bundle path of the original>#<chunk number>', e.g. 'Acme/references/srs.pdf#75'. Set by code from the chunks the note was written from.",
        question="Which chunks of which original is this note from?",
    )
