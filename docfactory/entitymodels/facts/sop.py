from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.entitymodels.items.sop_procedure import SopProcedure


class Sop(DocFactoryModel):
    """The Standard Operating Procedures (SOPs) of an application: repeatable operational tasks with steps."""

    procedures: list[SopProcedure] = doc_field(
        default_factory=list,
        description="The procedures, one entry each, e.g. a procedure named 'Restart the order service'. An empty list means none have been recorded yet.",
        question="Which standard operating procedures exist?",
    )
    notes: str = doc_field(
        default='',
        description="Free-text context about the procedures as a whole, e.g. 'Procedures are reviewed twice a year.' Leave empty when there is nothing to add.",
        question="Is there any additional context about these procedures?",
    )
