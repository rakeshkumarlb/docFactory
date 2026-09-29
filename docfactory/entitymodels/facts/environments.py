from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.entitymodels.items.environment import Environment


class Environments(DocFactoryModel):
    """The deployment environments of an application (e.g. Development, Test, Production)."""

    environments: list[Environment] = doc_field(
        default_factory=list,
        description="The environments, one entry each, e.g. an environment named 'Production'. An empty list means none have been described yet.",
        question="Which environments does the application run in?",
    )
    notes: str = doc_field(
        default='',
        description="Free-text context about the environments as a whole, e.g. 'Test and UAT share one cluster.' Leave empty when there is nothing to add.",
        question="Is there any additional context about the environments?",
    )
