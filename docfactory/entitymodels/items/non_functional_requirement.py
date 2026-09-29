from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable
from docfactory.entitymodels.items.non_functional_category import NonFunctionalCategory
from docfactory.entitymodels.items.requirement_priority import RequirementPriority


class NonFunctionalRequirement(DocFactoryModel):
    """One non-functional (quality) requirement of an application, e.g. a performance or security requirement, with its measurable target."""

    id: str = doc_field(
        description="Identifier used to refer to the requirement, e.g. 'NFR-001'. Identifies the requirement.",
        question="What is the identifier of this non-functional requirement?",
        min_length=1,
    )
    category: NonFunctionalCategory = doc_field(
        description="Quality category: PERFORMANCE, AVAILABILITY, SECURITY, USABILITY, MAINTAINABILITY, COMPLIANCE or OTHER, e.g. PERFORMANCE.",
        question="Which quality category does this requirement belong to?",
    )
    statement: str = doc_field(
        description="What quality the system must have, e.g. 'The dashboard shall load within 2 seconds for typical users.'",
        question="What does this non-functional requirement state?",
        min_length=1,
    )
    target: str | NotApplicable | None = doc_field(
        default=None,
        description="The measurable target, e.g. '95th percentile page load under 2 seconds'. N/A with a reason when the requirement cannot be measured.",
        question="What is the measurable target of this requirement?",
        na_allowed=True,
    )
    priority: RequirementPriority | None = doc_field(
        default=None,
        description="MoSCoW priority: MUST, SHOULD, COULD or WONT, e.g. SHOULD. Leave empty when not yet prioritised.",
        question="What is the priority (MUST, SHOULD, COULD or WONT) of this requirement?",
    )
    verification: str | NotApplicable | None = doc_field(
        default=None,
        description="How the requirement is verified, e.g. 'Monthly load test against the staging environment'. N/A with a reason when it is not verified separately.",
        question="How is this requirement verified?",
        na_allowed=True,
    )
