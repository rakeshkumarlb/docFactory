from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.documentmodels.entitybound.application_summary_section import ApplicationSummarySection
from docfactory.documentmodels.entitybound.monitoring_section import MonitoringSection
from docfactory.documentmodels.entitybound.sop_section import SopSection
from docfactory.documentmodels.entitybound.support_section import SupportSection


class SopDocument(DocFactoryModel):
    """The SOP (Standard Operating Procedures) document body: how the application is monitored and supported and the runbooks operators follow, without document control or revision history."""

    application_summary: ApplicationSummarySection = doc_field(
        description="The application-summary section: the essential facts about what the application is and who it serves, e.g. a section carrying the application's name, purpose and target users. A good value is a fully composed ApplicationSummarySection.",
        question="What is the application summary for this document?",
        binding="composed",
    )
    monitoring: MonitoringSection = doc_field(
        description="The monitoring section: tools, key metrics, alerts, dashboards and log locations, e.g. a section naming the monitoring tools and alerts. A good value is a fully composed MonitoringSection.",
        question="What is the monitoring setup for this document?",
        binding="composed",
    )
    support: SupportSection = doc_field(
        description="The support section: support model, contacts, escalation, incident handling and runbooks, e.g. a section listing support levels and contacts. A good value is a fully composed SupportSection.",
        question="What is the support model for this document?",
        binding="composed",
    )
    standard_operating_procedures: SopSection = doc_field(
        description="The standard-operating-procedures section: repeatable operational tasks with steps, e.g. a section describing how to restart a service. A good value is a fully composed SopSection.",
        question="What are the standard operating procedures for this document?",
        binding="composed",
    )
