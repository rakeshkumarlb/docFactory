from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class SloObjective(DocFactoryModel):
    """One Service Level Objective (SLO): a measurable reliability or performance target with how it is measured."""

    name: str = doc_field(
        description="Short name of the objective, e.g. 'API availability'. Identifies the SLO.",
        question="What is the name of this objective?",
        min_length=1,
    )
    definition: str = doc_field(
        default='',
        description="What is being promised and how it is defined, e.g. 'Share of successful API requests out of all requests.' Leave empty when not yet defined.",
        question="How is this objective defined?",
    )
    target: str = doc_field(
        default='',
        description="The target value, e.g. '99.9%'. Leave empty when no target has been set.",
        question="What is the target value of this objective?",
    )
    measurement_window: str = doc_field(
        default='',
        description="The period the target is measured over, e.g. 'Rolling 30 days'. Leave empty when not yet decided.",
        question="Over which period is this objective measured?",
    )
    measurement_source: str = doc_field(
        default='',
        description="System or report the measurement comes from, e.g. 'Monitoring dashboard - API availability'. Leave empty when not yet known.",
        question="Where is this objective measured?",
    )
    breach_consequence: str = doc_field(
        default='',
        description="What happens when the target is missed, e.g. 'Post-incident review and a service credit.' Leave empty when not yet defined.",
        question="What are the consequences of breaching this objective?",
    )
