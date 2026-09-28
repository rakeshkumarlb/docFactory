from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.alert import Alert


class Monitoring(DocFactoryModel):
    """How an application is monitored: tools, key metrics, alerts, dashboards and where logs are kept."""

    monitoring_tools: list[str] = doc_field(
        default_factory=list,
        description="The monitoring tools used, e.g. ['Prometheus', 'Grafana']. An empty list means none have been recorded yet.",
        question="Which monitoring tools are used?",
    )
    key_metrics: list[str] = doc_field(
        default_factory=list,
        description="The key metrics watched, e.g. ['Request latency', 'Error rate']. An empty list means none have been recorded yet.",
        question="Which key metrics are monitored?",
    )
    alerts: list[Alert] = doc_field(
        default_factory=list,
        description="The alerts configured, one entry each, e.g. an alert named 'High API error rate'. An empty list means none have been described yet.",
        question="Which alerts are configured?",
    )
    dashboards: list[str] = doc_field(
        default_factory=list,
        description="Dashboards, as names or links, e.g. ['Grafana - API overview']. An empty list means none have been recorded yet.",
        question="Which dashboards exist?",
    )
    log_locations: list[str] = doc_field(
        default_factory=list,
        description="Where logs can be found, e.g. ['CloudWatch log group /app/api']. An empty list means none have been recorded yet.",
        question="Where are the application logs stored?",
    )
