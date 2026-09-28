from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.slo_objective import SloObjective


class SloSection(DocFactoryModel):
    """The Slo section of a document, mirrored from the Slo entity: the Service Level Objectives (SLOs) common to all applications, e.g. shared availability and latency targets."""

    objectives: list[SloObjective] = doc_field(
        default_factory=list,
        description="The objectives, one entry each, e.g. an objective named 'API availability'. An empty list means none have been defined yet.",
        question="Which service level objectives apply?",
        binding="Slo.objectives",
        render_as="table",
    )
    notes: str = doc_field(
        default='',
        description="Free-text context about the shared SLOs as a whole, e.g. 'Reviewed every year by the service owners.' Leave empty when there is nothing to add.",
        question="Is there any additional context about these SLOs?",
        binding="Slo.notes",
    )
