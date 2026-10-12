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

    additional_information: list[str] = doc_field(
        default_factory=list,
        description="Further statements the document makes about this item that fit none of its other fields, one per statement, e.g. ['Listed under Server Infrastructure in the hardware interfaces.']. Only what the text states; empty when there is nothing more.",
        scored=False, in_documents=False,
    )

    evidence: list[str] = doc_field(
        default_factory=list,
        description="Where the document states this item, one entry per place as '<heading trail> (chunk N): <the line>', e.g. ['4.2. Hardware Interfaces (chunk 40): - Application servers']. Set by code from the chunks; leave it empty.",
        scored=False, in_documents=False,
    )
