from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class SupportContact(DocFactoryModel):
    """One level or role of application support, with the team, how to reach it and when."""

    role: str = doc_field(
        description="The support role or level, e.g. 'L2 application support'. Identifies the contact.",
        question="What is the support role or level?",
        min_length=1,
    )
    team: str = doc_field(
        default='',
        description="Team or group filling the role, e.g. 'Application Operations'. A good value names a team, not an individual.",
        question="Which team fills this support role?",
    )
    contact_channel: str = doc_field(
        default='',
        description="How to reach the team, e.g. 'support@example.test' or 'Slack #app-support'. Leave empty when not yet known.",
        question="How is this support contact reached?",
    )
    support_hours: str = doc_field(
        default='',
        description="When the contact is available, e.g. 'Mon-Fri 08:00-18:00 CET' or '24x7'. Leave empty when not yet known.",
        question="During which hours is this contact available?",
    )
    escalates_to: str = doc_field(
        default='',
        description="The role this contact escalates to when it cannot resolve an issue, e.g. 'L3 development team'. Leave empty when not yet known.",
        question="Who does this contact escalate to?",
    )
