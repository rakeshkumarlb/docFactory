from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.environment import Environment


class EnvironmentsSection(DocFactoryModel):
    """The Environments section of a document, mirrored from the Environments entity: the deployment environments of an application (e.g. Development, Test, Production)."""

    environments: list[Environment] = doc_field(
        default_factory=list,
        description="The environments, one entry each, e.g. an environment named 'Production'. An empty list means none have been described yet.",
        question="Which environments does the application run in?",
        binding="Environments.environments",
        render_as="table",
    )
    notes: str = doc_field(
        default='',
        description="Free-text context about the environments as a whole, e.g. 'Test and UAT share one cluster.' Leave empty when there is nothing to add.",
        question="Is there any additional context about the environments?",
        binding="Environments.notes",
    )
