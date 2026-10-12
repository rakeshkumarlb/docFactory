from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.entitymodels.items.relation import Relation


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

    relations: list[Relation] = doc_field(
        default_factory=list,
        description="Relationships this item states about other items of the document, one per other item, e.g. [{'target': 'FR-03', 'kind': 'depends_on'}]. Only what the text states; empty when it states none.",
        scored=False, in_documents=False,
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
