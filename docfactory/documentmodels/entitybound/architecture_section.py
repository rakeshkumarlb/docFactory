from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable
from docfactory.models.component import Component
from docfactory.models.data_store import DataStore
from docfactory.models.integration import Integration


class ArchitectureSection(DocFactoryModel):
    """The Architecture section of a document, mirrored from the Architecture entity: the architecture of an application or of one of its components: style, technology stack, components, data stores and integrations with other systems."""

    architecture_style: str = doc_field(
        default='',
        description="Overall architectural style, e.g. 'Modular monolith' or 'Microservices behind an API gateway'. Leave empty when not yet described.",
        question="What is the overall architectural style?",
        binding="Architecture.architecture_style",
    )
    technology_stack: list[str] = doc_field(
        default_factory=list,
        description="Main technologies used, one entry each, e.g. ['Python 3.12', 'PostgreSQL 16']. An empty list means the stack has not been recorded yet.",
        question="Which technologies make up the technology stack?",
        binding="Architecture.technology_stack",
    )
    components: list[Component] = doc_field(
        default_factory=list,
        description="The components of the architecture, one entry each, e.g. a component named 'Order API'. An empty list means none have been described yet.",
        question="Which components make up the architecture?",
        binding="Architecture.components",
        render_as="table",
    )
    data_stores: list[DataStore] = doc_field(
        default_factory=list,
        description="The data stores used, one entry each, e.g. a store named 'Orders database'. An empty list means none have been described yet.",
        question="Which data stores does the application use?",
        binding="Architecture.data_stores",
        render_as="table",
    )
    integrations: list[Integration] = doc_field(
        default_factory=list,
        description="The integrations with other systems, one entry each, e.g. an integration named 'Payment gateway'. An empty list means none have been described yet.",
        question="Which other systems does the application integrate with?",
        binding="Architecture.integrations",
        render_as="table",
    )
    diagram_reference: str | NotApplicable | None = doc_field(
        default=None,
        description="Relative path with forward slashes to an architecture diagram, e.g. 'docs/diagrams/architecture.png'. N/A with a reason when no diagram exists.",
        question="Where is the architecture diagram stored?",
        na_allowed=True,
        binding="Architecture.diagram_reference",
    )
    notes: str = doc_field(
        default='',
        description="Free-text context about the architecture, e.g. 'The reporting component is being replaced in 2027.' Leave empty when there is nothing to add.",
        question="Is there any additional context about the architecture?",
        binding="Architecture.notes",
    )
