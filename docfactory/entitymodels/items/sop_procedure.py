from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class SopProcedure(DocFactoryModel):
    """One Standard Operating Procedure (SOP): a repeatable operational task with its trigger, roles, ordered steps and verification."""

    name: str = doc_field(
        description="Name of the procedure, e.g. 'Restart the order service'. Identifies the procedure.",
        question="What is the name of this procedure?",
        min_length=1,
    )
    purpose: str = doc_field(
        default='',
        description="Why the procedure exists and what it achieves, e.g. 'Restore the order service after it becomes unresponsive.' Leave empty when not yet described.",
        question="What is the purpose of this procedure?",
    )
    trigger: str = doc_field(
        default='',
        description="When the procedure is performed, e.g. 'When the High API error rate alert fires.' Leave empty when not yet known.",
        question="When is this procedure performed?",
    )
    frequency: str = doc_field(
        default='',
        description="How often it is performed, e.g. 'On demand', 'Monthly'. Leave empty when not yet known.",
        question="How often is this procedure performed?",
    )
    roles: list[str] = doc_field(
        default_factory=list,
        description="Roles that perform or approve the procedure, e.g. ['Operations engineer']. An empty list means none have been recorded yet.",
        question="Which roles perform this procedure?",
    )
    prerequisites: list[str] = doc_field(
        default_factory=list,
        description="What must be in place before starting, e.g. ['Access to the production console']. An empty list means none have been recorded yet.",
        question="What are the prerequisites for this procedure?",
    )
    steps: list[str] = doc_field(
        default_factory=list,
        description="The ordered steps, one action per entry, e.g. ['Log in to the console', 'Restart the service']. An empty list means the steps have not been recorded yet.",
        question="What are the steps of this procedure, in order?",
        render_as="numbered",
    )
    verification: str = doc_field(
        default='',
        description="How to confirm the procedure succeeded, e.g. 'The health endpoint returns 200.' Leave empty when not yet defined.",
        question="How is success of this procedure verified?",
    )
    escalation: str = doc_field(
        default='',
        description="What to do when it fails, e.g. 'Escalate to L3 support.' Leave empty when not yet defined.",
        question="What is the escalation when this procedure fails?",
    )
