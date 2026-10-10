from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.documentmodels.revision_entry import RevisionEntry


class RevisionHistory(DocFactoryModel):
    """The revision history of one generated document: the ordered list of past revisions. Never derived from knowledge facts: maintained by the generate process, which adds one entry each time the document body changes (the seeds supply it in Phase 1). Reused by every document type."""

    revisions: list[RevisionEntry] = doc_field(
        default_factory=list,
        description="The revisions recorded for this document, oldest first, e.g. a first entry with version '1.0' and summary 'Initial draft created.' An empty list means no revision has been recorded yet.",
        question="What revisions have been made to this document?",
    )
    notes: str = doc_field(
        default='',
        description="Free-text context about the revision history as a whole, e.g. 'Reviewed and re-issued after each major release.' Leave empty when there is nothing to add.",
        question="Is there any additional context about how this document's revisions are managed?",
    )
