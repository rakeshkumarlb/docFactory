from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.documentmodels.entitybound.application_summary_section import ApplicationSummarySection
from docfactory.documentmodels.entitybound.architecture_section import ArchitectureSection
from docfactory.documentmodels.entitybound.backup_recovery_section import BackupRecoverySection
from docfactory.documentmodels.entitybound.deployment_section import DeploymentSection
from docfactory.documentmodels.entitybound.environments_section import EnvironmentsSection
from docfactory.documentmodels.entitybound.known_errors_section import KnownErrorsSection
from docfactory.documentmodels.entitybound.kpi_summary_section import KpiSummarySection
from docfactory.documentmodels.entitybound.monitoring_section import MonitoringSection
from docfactory.documentmodels.entitybound.slo_section import SloSection
from docfactory.documentmodels.entitybound.sop_section import SopSection
from docfactory.documentmodels.entitybound.support_section import SupportSection


class SmtdDocument(DocFactoryModel):
    """The SMTD (System Maintenance and Technical Document) body: application summary, architecture, environments, deployment, monitoring, backup and recovery, support, known errors, standard operating procedures, service levels and KPIs, without document control or revision history."""

    application_summary: ApplicationSummarySection = doc_field(
        description="The application-summary section: the essential facts about what the application is and who it serves, e.g. a section carrying the application's name, purpose and target users. A good value is a fully composed ApplicationSummarySection.",
        question="What is the application summary for this document?",
        binding="composed",
    )
    architecture: ArchitectureSection = doc_field(
        description="The architecture section: style, technology stack, components, data stores and integrations, e.g. a section describing a modular monolith with one database. A good value is a fully composed ArchitectureSection.",
        question="What is the architecture for this document?",
        binding="composed",
    )
    environments: EnvironmentsSection = doc_field(
        description="The environments section: the deployment environments of the application, e.g. a section listing Development, Test and Production. A good value is a fully composed EnvironmentsSection.",
        question="What are the environments for this document?",
        binding="composed",
    )
    deployment: DeploymentSection = doc_field(
        description="The deployment section: how the application is built, released and rolled back, e.g. a section describing a pipeline-driven release. A good value is a fully composed DeploymentSection.",
        question="What is the deployment approach for this document?",
        binding="composed",
    )
    monitoring: MonitoringSection = doc_field(
        description="The monitoring section: tools, key metrics, alerts, dashboards and log locations, e.g. a section naming the monitoring tools and alerts. A good value is a fully composed MonitoringSection.",
        question="What is the monitoring setup for this document?",
        binding="composed",
    )
    backup_recovery: BackupRecoverySection = doc_field(
        description="The backup and recovery section: backups, restore and recovery objectives, e.g. a section giving the backup schedule, RPO and RTO. A good value is a fully composed BackupRecoverySection.",
        question="What is the backup and recovery approach for this document?",
        binding="composed",
    )
    support: SupportSection = doc_field(
        description="The support section: support model, contacts, escalation, incident handling and runbooks, e.g. a section listing support levels and contacts. A good value is a fully composed SupportSection.",
        question="What is the support model for this document?",
        binding="composed",
    )
    known_errors: KnownErrorsSection = doc_field(
        description="The known-errors section: known errors with symptoms, workaround and fix status, e.g. a section listing a known report-export timeout. A good value is a fully composed KnownErrorsSection.",
        question="What are the known errors for this document?",
        binding="composed",
    )
    standard_operating_procedures: SopSection = doc_field(
        description="The standard-operating-procedures section: repeatable operational tasks with steps, e.g. a section describing how to restart a service. A good value is a fully composed SopSection.",
        question="What are the standard operating procedures for this document?",
        binding="composed",
    )
    service_levels: SloSection = doc_field(
        description="The service-levels section: the shared Service Level Objectives that apply, e.g. a section listing an availability objective. A good value is a fully composed SloSection.",
        question="What are the service levels for this document?",
        binding="composed",
    )
    kpi_summary: KpiSummarySection = doc_field(
        description="The KPI section: the shared KPIs tracked for the application, e.g. a section listing KPIs such as 'On-time order fulfillment rate'. A good value is a fully composed KpiSummarySection.",
        question="What are the tracked KPIs for this document?",
        binding="composed",
    )
