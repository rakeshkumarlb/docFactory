from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.entitymodels.items.alert import Alert


class MonitoringSection(DocFactoryModel):
    """The Monitoring section of a document, mirrored from the Monitoring entity: how an application is monitored: tools, key metrics, alerts, dashboards and where logs are kept."""

    monitoring_tools: list[str] = doc_field(
        default_factory=list,
        description="The monitoring tools used, e.g. ['Prometheus', 'Grafana']. An empty list means none have been recorded yet.",
        question="Which monitoring tools are used?",
        binding="Monitoring.monitoring_tools",
    )
    key_metrics: list[str] = doc_field(
        default_factory=list,
        description="The key metrics watched, e.g. ['Request latency', 'Error rate']. An empty list means none have been recorded yet.",
        question="Which key metrics are monitored?",
        binding="Monitoring.key_metrics",
    )
    alerts: list[Alert] = doc_field(
        default_factory=list,
        description="The alerts configured, one entry each, e.g. an alert named 'High API error rate'. An empty list means none have been described yet.",
        question="Which alerts are configured?",
        binding="Monitoring.alerts",
        render_as="table",
    )
    dashboards: list[str] = doc_field(
        default_factory=list,
        description="Dashboards, as names or links, e.g. ['Grafana - API overview']. An empty list means none have been recorded yet.",
        question="Which dashboards exist?",
        binding="Monitoring.dashboards",
    )
    log_locations: list[str] = doc_field(
        default_factory=list,
        description="Where logs can be found, e.g. ['CloudWatch log group /app/api']. An empty list means none have been recorded yet.",
        question="Where are the application logs stored?",
        binding="Monitoring.log_locations",
    )
