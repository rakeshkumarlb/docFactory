from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.kpi import Kpi


class KpiSummarySection(DocFactoryModel):
    """The KPI section of a document: the shared KPIs tracked, mirrored from Kpis."""

    kpis: list[Kpi] = doc_field(
        default_factory=list,
        description="The KPIs tracked, one entry per indicator, e.g. a KPI named 'On-time order fulfillment rate'. An empty list means no KPI has been defined yet.",
        question="Which KPIs are tracked?",
        binding="Kpis.kpis",
        render_as="table",
    )
    notes: str = doc_field(
        default='',
        description="Free-text context about the shared KPI set as a whole, e.g. 'Reviewed quarterly by the leadership team.' Leave empty when there is nothing to add.",
        question="Is there any additional context about how these KPIs are governed or reviewed?",
        binding="Kpis.notes",
    )
