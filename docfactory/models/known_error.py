from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable


class KnownError(DocFactoryModel):
    """One known error of an application: its symptoms, cause, workaround and fix status."""

    title: str = doc_field(
        description="Short title of the known error, e.g. 'Report export times out for large date ranges'. Identifies the error.",
        question="What is the title of this known error?",
        min_length=1,
    )
    error_id: str = doc_field(
        default='',
        description="Identifier used to refer to the error, e.g. 'KE-001'. Leave empty when no identifier has been assigned.",
        question="What is the identifier of this known error?",
    )
    symptoms: str = doc_field(
        default='',
        description="What users or operators see when it occurs, e.g. 'The export page shows a timeout message after 60 seconds.' Leave empty when not yet described.",
        question="What are the symptoms of this known error?",
    )
    cause: str = doc_field(
        default='',
        description="The root cause, e.g. 'The export query has no index on the date column.' Leave empty when the cause is not yet known.",
        question="What causes this known error?",
    )
    workaround: str = doc_field(
        default='',
        description="How to work around it until fixed, e.g. 'Export in ranges of at most 7 days.' Leave empty when no workaround exists yet.",
        question="Is there a workaround for this known error?",
    )
    permanent_fix: str | NotApplicable | None = doc_field(
        default=None,
        description="The planned permanent fix, e.g. 'Add a database index in release 2.4.' N/A with a reason when no fix is planned.",
        question="What is the permanent fix for this known error?",
        na_allowed=True,
    )
    severity: str = doc_field(
        default='',
        description="Impact of the error, e.g. 'High', 'Medium', 'Low'. Leave empty when not yet classified.",
        question="What is the severity of this known error?",
    )
    status: str = doc_field(
        default='',
        description="Current state of the error, e.g. 'Open', 'Workaround available', 'Fixed'. Leave empty when not yet recorded.",
        question="What is the current status of this known error?",
    )
    related_ticket: str | NotApplicable | None = doc_field(
        default=None,
        description="Reference to the tracking ticket, e.g. 'JIRA-1234'. N/A with a reason when no ticket exists.",
        question="Which ticket tracks this known error?",
        na_allowed=True,
    )
