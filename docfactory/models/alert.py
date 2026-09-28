from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class Alert(DocFactoryModel):
    """One monitoring alert: what triggers it, how severe it is and what to do when it fires."""

    name: str = doc_field(
        description="Name of the alert, e.g. 'High API error rate'. Identifies the alert.",
        question="What is the name of this alert?",
        min_length=1,
    )
    condition: str = doc_field(
        default='',
        description="The condition that fires the alert, e.g. '5xx responses above 2% for 5 minutes.' A good value states the metric and threshold.",
        question="Under which condition does this alert fire?",
    )
    severity: str = doc_field(
        default='',
        description="How serious the alert is, e.g. 'Critical', 'Warning'. Leave empty when not yet classified.",
        question="What is the severity of this alert?",
    )
    response_action: str = doc_field(
        default='',
        description="What the responder should do when the alert fires, e.g. 'Check the API logs and restart the service if it is unresponsive.' Leave empty when not yet defined.",
        question="What should be done when this alert fires?",
    )
    notification_channel: str = doc_field(
        default='',
        description="Where the alert is sent, e.g. 'PagerDuty on-call rotation' or 'Email to ops-team'. Leave empty when not yet known.",
        question="Where is this alert delivered?",
    )
