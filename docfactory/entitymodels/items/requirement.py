from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.requirement_priority import RequirementPriority


class Requirement(DocFactoryModel):
    """One functional requirement of an application: what the system must do, with its priority and acceptance criteria."""

    id: str = doc_field(
        description="Identifier used to refer to the requirement, e.g. 'FR-001'. Identifies the requirement.",
        question="What is the identifier of this requirement?",
        min_length=1,
    )
    title: str = doc_field(
        description="Short title of the requirement, e.g. 'Scan a repository on push'.",
        question="What is the title of this requirement?",
        min_length=1,
    )
    description: str = doc_field(
        description="What the system must do, e.g. 'The system shall start a scan whenever a commit is pushed to a connected repository.'",
        question="What does this requirement state?",
        min_length=1,
    )
    priority: RequirementPriority | None = doc_field(
        default=None,
        description="MoSCoW priority: MUST, SHOULD, COULD or WONT, e.g. MUST. Leave empty when not yet prioritised.",
        question="What is the priority (MUST, SHOULD, COULD or WONT) of this requirement?",
    )
    rationale: str | NotApplicable | None = doc_field(
        default=None,
        description="Why the requirement exists, e.g. 'Maintainers must not run README updates by hand.' N/A with a reason when no rationale applies.",
        question="Why does this requirement exist?",
        na_allowed=True,
    )
    acceptance_criteria: list[str] = doc_field(
        default_factory=list,
        description="Testable conditions that show the requirement is met, e.g. ['A scan starts within 60 seconds of a push']. An empty list means none recorded yet.",
        question="What are the acceptance criteria of this requirement?",
    )
