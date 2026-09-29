from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable


class Kpi(DocFactoryModel):
    """One Key Performance Indicator (KPI) used to measure how well an application or a business process is performing."""

    name: str = doc_field(
        description="Short name of the KPI, e.g. 'On-time order fulfillment rate'. Identifies what is being measured.",
        question="What is the name of this KPI?",
        min_length=1,
    )
    definition: str = doc_field(
        description="What the KPI measures and how it is calculated, e.g. 'Percentage of orders delivered within the promised time window, computed monthly from order timestamps.' A good value states the formula or method, not just a label.",
        question="What does this KPI measure and how is it calculated?",
        min_length=1,
    )
    unit: str = doc_field(
        default='',
        description="Unit the KPI value is expressed in, e.g. '%', 'minutes', 'count per day'. Leave empty when no unit has been defined yet.",
        question="What unit is this KPI measured in?",
    )
    target: str = doc_field(
        default='',
        description="The target or threshold value the organisation aims for, e.g. '>= 95%'. Leave empty when no target has been set yet.",
        question="What is the target or threshold value for this KPI?",
    )
    current_value: str = doc_field(
        default='',
        description="The most recently known value of the KPI, e.g. '92%'. Leave empty when no measurement has been recorded yet.",
        question="What is the current or most recently measured value of this KPI?",
    )
    measurement_frequency: str = doc_field(
        default='',
        description="How often the KPI is measured or reported, e.g. 'Monthly'. Leave empty when this has not been decided yet.",
        question="How often is this KPI measured or reported?",
    )
    owner: str = doc_field(
        default='',
        description="Role or team accountable for tracking and improving this KPI, e.g. 'Operations Manager'. A good value names a role or team, not an individual.",
        question="Who owns this KPI?",
    )
    data_source: str | NotApplicable | None = doc_field(
        default=None,
        description="System or report the KPI value is retrieved from, e.g. 'BI dashboard - Orders report'. N/A with a reason when the KPI is tracked manually and has no dedicated data source.",
        question="Where does the value for this KPI come from?",
        na_allowed=True,
    )
