from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.documentmodels.application_summary_section import ApplicationSummarySection
from docfactory.documentmodels.kpi_summary_section import KpiSummarySection


class OverviewDocument(DocFactoryModel):
    """The Overview document body: an application summary and its tracked KPIs, without document control or revision history."""

    application_summary: ApplicationSummarySection = doc_field(
        description="The application-summary section: the essential facts about what the application is and who it serves, e.g. a section carrying the application's name, purpose and target users. A good value is a fully composed ApplicationSummarySection.",
        question="What is the application summary for this document?",
        binding="composed",
    )
    kpi_summary: KpiSummarySection = doc_field(
        description="The KPI section: the shared KPIs tracked for the application, e.g. a section listing KPIs such as 'On-time order fulfillment rate'. A good value is a fully composed KpiSummarySection.",
        question="What are the tracked KPIs for this document?",
        binding="composed",
    )
