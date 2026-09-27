from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class ApplicationSummarySection(DocFactoryModel):
    """The application-summary section of a document: the essential facts about what the application is and who it serves, mirrored from ApplicationOverview."""

    application_name: str = doc_field(
        description="Official name of the application as used in documents, e.g. KitchenHQ. Identifies what this document is about.",
        question="What is the official name of the application?",
        min_length=1,
        binding="ApplicationOverview.application_name",
    )
    purpose: str = doc_field(
        description="One to three sentences on why the application exists and what problem it solves, e.g. 'Lets kitchen staff plan orders and track stock in one place.' A good value states the problem and the outcome, not the technology.",
        question="What is the purpose of the application: what problem does it solve and for whom?",
        min_length=1,
        binding="ApplicationOverview.purpose",
    )
    business_overview: str = doc_field(
        default='',
        description="Business context: the business area or process the application supports and the value it brings, e.g. 'Supports daily food ordering for all restaurants of the group and reduces waste.' A good value is a short paragraph a non-technical reader understands.",
        question="What is the business context of the application and which business process does it support?",
        binding="ApplicationOverview.business_overview",
    )
    target_users: list[str] = doc_field(
        default_factory=list,
        description="The kinds of users or user groups that use the application, one entry per group, e.g. ['Kitchen staff', 'Restaurant managers']. A good value names roles, not individuals.",
        question="Which user groups or roles use the application?",
        binding="ApplicationOverview.target_users",
    )
    key_capabilities: list[str] = doc_field(
        default_factory=list,
        description="The main things the application can do, one short statement per capability, e.g. ['Create and approve purchase orders', 'Track stock levels']. A good value is a business capability, not a screen or a technical feature.",
        question="What are the main capabilities or functions of the application?",
        binding="ApplicationOverview.key_capabilities",
    )
    business_criticality: str = doc_field(
        default='',
        description="How important the application is to the business and what an outage means, e.g. 'Tier 1 - business critical, orders stop without it'. A good value states the tier or level and the reason.",
        question="How business-critical is the application and what happens if it is unavailable?",
        binding="ApplicationOverview.business_criticality",
    )
