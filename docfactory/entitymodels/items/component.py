from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.entitymodels.items.relation import Relation


class Component(DocFactoryModel):
    """One deployable or logical component of an application's architecture (e.g. a web front end, an API service, a background worker)."""

    name: str = doc_field(
        description="Short name of the component, e.g. 'Web front end' or 'Order API'. Identifies the component within the application.",
        question="What is the name of this component?",
        min_length=1,
    )
    purpose: str = doc_field(
        default='',
        description="What the component does and why it exists, e.g. 'Serves the browser UI and forwards requests to the Order API.' Leave empty when not yet described.",
        question="What is the purpose of this component?",
    )
    technology: str = doc_field(
        default='',
        description="Main technology or framework the component is built with, e.g. 'Python 3.12 / FastAPI'. Leave empty when not yet known.",
        question="Which technology is this component built with?",
    )
    owner: str = doc_field(
        default='',
        description="Role or team responsible for the component, e.g. 'Platform team'. A good value names a role or team, not an individual.",
        question="Which team or role owns this component?",
    )
    dependencies: list[str] = doc_field(
        default_factory=list,
        description="Names of the other components, services or libraries this component depends on, e.g. ['Order database', 'Payment gateway']. An empty list means none have been recorded yet.",
        question="Which other components or services does this component depend on?",
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
