from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class DocumentControl(DocFactoryModel):
    """Document control metadata for one generated document: identity, version label, status, ownership, approvers and key dates. Never derived from knowledge facts: created and maintained by the generate process (the seeds supply it in Phase 1); the approvers are added by the human approval (Phase 5). Reused by every document type."""

    document_id: str = doc_field(
        description="Unique identifier of this document, e.g. 'KitchenHQ-SMTD-001'. Identifies which document this control record belongs to.",
        question="What is the unique document identifier?",
        min_length=1,
    )
    title: str = doc_field(
        description="Full title of the document as it appears on its cover page, e.g. 'KitchenHQ Software Maintenance and Transition Document'. A good value is the complete, human-readable document name.",
        question="What is the full title of the document?",
        min_length=1,
    )
    document_version: str = doc_field(
        default='',
        description="Version label of the document itself as shown on its cover page, e.g. '1.0'. Distinct from the stored row's Version counter; this is the document's own version number. Empty when not yet assigned.",
        question="What is the document's own version label, e.g. 1.0?",
    )
    status: str = doc_field(
        default='',
        description="Lifecycle status of the document, e.g. 'Draft', 'In review' or 'Approved'. A good value is a short phrase matching the organisation's document workflow. Empty when not yet set.",
        question="What is the current status of the document?",
    )
    owner: str = doc_field(
        default='',
        description="Person or role accountable for the content and upkeep of the document, e.g. 'QA Lead'. A good value names a role or team, not just a first name. Empty when not yet assigned.",
        question="Who owns this document?",
    )
    approvers: list[str] = doc_field(
        default_factory=list,
        description="Names or roles of the people who must approve or sign off the document, e.g. ['Engineering Manager', 'QA Lead']. An empty list means no approvers have been defined yet.",
        question="Who needs to approve this document?",
    )
    created_date: str | None = doc_field(
        default=None,
        description="Date the document was first created, ISO format YYYY-MM-DD, e.g. '2024-01-15'. Left empty when the creation date is not yet known.",
        question="On what date was this document created (YYYY-MM-DD)?",
    )
    last_updated_date: str | None = doc_field(
        default=None,
        description="Date the document was last updated, ISO format YYYY-MM-DD, e.g. '2024-02-01'. Left empty when it has not been updated since creation.",
        question="On what date was this document last updated (YYYY-MM-DD)?",
    )
