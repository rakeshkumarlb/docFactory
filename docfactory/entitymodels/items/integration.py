from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class Integration(DocFactoryModel):
    """One connection between an application and another system, with the direction, protocol and data exchanged."""

    name: str = doc_field(
        description="Name of the other system the application integrates with, e.g. 'Payment gateway'. Identifies the integration.",
        question="Which other system does the application integrate with?",
        min_length=1,
    )
    direction: str = doc_field(
        default='',
        description="Direction of the data flow as seen from this application: 'inbound', 'outbound' or 'bidirectional', e.g. 'outbound'. Leave empty when not yet known.",
        question="Is the integration inbound, outbound or bidirectional?",
    )
    protocol: str = doc_field(
        default='',
        description="Protocol or interface technology used, e.g. 'REST over HTTPS', 'SFTP', 'AMQP'. Leave empty when not yet known.",
        question="Which protocol or interface does the integration use?",
    )
    purpose: str = doc_field(
        default='',
        description="Why the integration exists, e.g. 'Submits payment requests and receives payment confirmations.' Leave empty when not yet described.",
        question="What is the purpose of this integration?",
    )
    data_exchanged: str = doc_field(
        default='',
        description="What data crosses the integration, e.g. 'Payment amount, order reference and payment status.' Leave empty when not yet known.",
        question="What data is exchanged over this integration?",
    )
    authentication: str = doc_field(
        default='',
        description="How the connection is authenticated, e.g. 'OAuth 2.0 client credentials'. Leave empty when not yet known.",
        question="How is this integration authenticated?",
    )
