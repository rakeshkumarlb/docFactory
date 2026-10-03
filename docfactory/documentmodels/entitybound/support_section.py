from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.entitymodels.items.support_contact import SupportContact


class SupportSection(DocFactoryModel):
    """The Support section of a document, mirrored from the Support entity: how an application is supported in operation: support model, contacts, escalation, incident handling and runbooks."""

    support_model: str = doc_field(
        default='',
        description="How support is organised, e.g. 'Three-level support with 24x7 on-call for critical incidents.' Leave empty when not yet described.",
        question="How is support organised?",
        binding="Support.support_model",
    )
    contacts: list[SupportContact] = doc_field(
        default_factory=list,
        description="The support contacts, one entry per level or role, e.g. a contact with role 'L2 application support'. An empty list means none have been described yet.",
        question="Who are the support contacts?",
        binding="Support.contacts",
        render_as="table",
    )
    escalation_path: str = doc_field(
        default='',
        description="The order in which issues are escalated, e.g. 'L1 helpdesk, then L2 operations, then L3 development.' Leave empty when not yet defined.",
        question="What is the escalation path?",
        binding="Support.escalation_path",
    )
    incident_process: str = doc_field(
        default='',
        description="How incidents are raised, handled and closed, e.g. 'Incidents are logged in the ticket system and triaged within 30 minutes.' Leave empty when not yet described.",
        question="How are incidents handled?",
        binding="Support.incident_process",
    )
    runbooks: list[str] = doc_field(
        default_factory=list,
        description="Runbooks, as titles or relative paths with forward slashes, e.g. ['docs/runbooks/restart-api.md']. An empty list means none have been recorded yet.",
        question="Which runbooks exist?",
        binding="Support.runbooks",
    )
