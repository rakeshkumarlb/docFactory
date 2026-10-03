from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.entitymodels.items.non_functional_requirement import NonFunctionalRequirement


class NonFunctionalRequirementsSection(DocFactoryModel):
    """The NonFunctionalRequirements section of a document, mirrored from the NonFunctionalRequirements entity: the quality requirements such as performance, availability and security targets."""

    summary: str = doc_field(
        default='',
        description="Short overview of the quality expectations, e.g. 'Interactive pages must feel instant and the service must be available during working hours.' Leave empty when not yet written.",
        question="How would you summarise the non-functional requirements?",
        binding="NonFunctionalRequirements.summary",
    )
    requirements: list[NonFunctionalRequirement] = doc_field(
        default_factory=list,
        description="The non-functional requirements, one entry each, e.g. 'NFR-001 Dashboard load time'. An empty list means none recorded yet.",
        question="Which non-functional requirements does the application have?",
        binding="NonFunctionalRequirements.requirements",
        render_as="table",
    )
