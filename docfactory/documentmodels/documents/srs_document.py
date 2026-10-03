from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.documentmodels.entitybound.application_summary_section import ApplicationSummarySection
from docfactory.documentmodels.entitybound.functional_requirements_section import FunctionalRequirementsSection
from docfactory.documentmodels.entitybound.non_functional_requirements_section import NonFunctionalRequirementsSection
from docfactory.documentmodels.entitybound.slo_section import SloSection


class SrsDocument(DocFactoryModel):
    """The SRS (Software Requirements Specification) body, without document control or revision history."""

    application_summary: ApplicationSummarySection = doc_field(
        description="The application-summary section: the essential facts about what the application is and who it serves, e.g. a section carrying the application's name, purpose and target users. A good value is a fully composed ApplicationSummarySection.",
        question="What is the application summary for this document?",
        binding="composed",
    )
    functional_requirements: FunctionalRequirementsSection = doc_field(
        description="The functional-requirements section: what the system must do and what is out of scope, e.g. a section listing 'Scan a repository on push'. A good value is a fully composed FunctionalRequirementsSection.",
        question="What are the functional requirements for this document?",
        binding="composed",
    )
    non_functional_requirements: NonFunctionalRequirementsSection = doc_field(
        description="The non-functional-requirements section: quality targets such as performance and availability, e.g. a section listing a dashboard load-time target. A good value is a fully composed NonFunctionalRequirementsSection.",
        question="What are the non-functional requirements for this document?",
        binding="composed",
    )
    service_levels: SloSection = doc_field(
        description="The service-levels section: the shared Service Level Objectives that apply, e.g. a section listing an availability objective. A good value is a fully composed SloSection.",
        question="What are the service levels for this document?",
        binding="composed",
    )
