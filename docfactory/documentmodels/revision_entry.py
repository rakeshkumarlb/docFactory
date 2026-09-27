from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class RevisionEntry(DocFactoryModel):
    """One entry in a document's revision history: a single version change together with its date, author and a summary of what changed."""

    version: str = doc_field(
        description="Version number this revision produced, e.g. '1.0'. Identifies which document version this entry describes.",
        question="Which document version does this revision entry describe?",
        min_length=1,
        binding="caller",
    )
    date: str = doc_field(
        description="Date this revision was made, ISO format YYYY-MM-DD, e.g. '2024-01-15'. Identifies when the change took effect.",
        question="On what date was this revision made (YYYY-MM-DD)?",
        min_length=1,
        binding="caller",
    )
    summary: str = doc_field(
        description="Short description of what changed in this revision, e.g. 'Initial draft created.' A good value states the concrete change, not just 'updated'.",
        question="What changed in this revision?",
        min_length=1,
        binding="caller",
    )
    author: str = doc_field(
        default='',
        description="Person or role who made this revision, e.g. 'Jane Doe'. Empty when the author was not recorded.",
        question="Who made this revision?",
        binding="caller",
    )
