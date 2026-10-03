from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


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
