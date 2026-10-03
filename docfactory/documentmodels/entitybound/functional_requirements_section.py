from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.requirement import Requirement


class FunctionalRequirementsSection(DocFactoryModel):
    """The FunctionalRequirements section of a document, mirrored from the FunctionalRequirements entity: what the system must do, plus what is explicitly out of scope."""

    summary: str = doc_field(
        default='',
        description="Short overview of the functional scope, e.g. 'ReadmeForge keeps repository READMEs current by proposing updates after each push.' Leave empty when not yet written.",
        question="How would you summarise the functional requirements?",
        binding="FunctionalRequirements.summary",
    )
    requirements: list[Requirement] = doc_field(
        default_factory=list,
        description="The functional requirements, one entry each, e.g. 'FR-001 Scan a repository on push'. An empty list means none recorded yet.",
        question="Which functional requirements does the application have?",
        binding="FunctionalRequirements.requirements",
        render_as="table",
    )
    out_of_scope: list[str] | NotApplicable = doc_field(
        default_factory=list,
        description="What the application deliberately does not do, e.g. ['Editing source code other than README files']. N/A with a reason when nothing is excluded.",
        question="What is explicitly out of scope?",
        na_allowed=True,
        binding="FunctionalRequirements.out_of_scope",
    )
