from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable


class ApplicationOverview(DocFactoryModel):
    """High-level overview of one software application: why it exists, who it serves and what it does. Common opening facts of application documents (BRD, SRS, SMTD)."""

    application_name: str = doc_field(
        description="Official name of the application as used in documents, e.g. KitchenHQ. Identifies what this overview is about.",
        question="What is the official name of the application?",
        min_length=1,
    )
    purpose: str = doc_field(
        description="One to three sentences on why the application exists and what problem it solves, e.g. 'Lets kitchen staff plan orders and track stock in one place.' A good value states the problem and the outcome, not the technology.",
        question="What is the purpose of the application: what problem does it solve and for whom?",
        min_length=1,
    )
    business_overview: str = doc_field(
        default='',
        description="Business context: the business area or process the application supports and the value it brings, e.g. 'Supports daily food ordering for all restaurants of the group and reduces waste.' A good value is a short paragraph a non-technical reader understands.",
        question="What is the business context of the application and which business process does it support?",
    )
    business_owner: str = doc_field(
        default='',
        description="Person, role or department accountable for the application from the business side, e.g. 'Head of Operations'. A good value names a role or a team, not just a first name.",
        question="Who is the business owner of the application?",
    )
    target_users: list[str] = doc_field(
        default_factory=list,
        description="The kinds of users or user groups that use the application, one entry per group, e.g. ['Kitchen staff', 'Restaurant managers']. A good value names roles, not individuals.",
        question="Which user groups or roles use the application?",
    )
    key_capabilities: list[str] = doc_field(
        default_factory=list,
        description="The main things the application can do, one short statement per capability, e.g. ['Create and approve purchase orders', 'Track stock levels']. A good value is a business capability, not a screen or a technical feature.",
        question="What are the main capabilities or functions of the application?",
    )
    out_of_scope: list[str] | NotApplicable = doc_field(
        default_factory=list,
        description="Things the application deliberately does not do, one statement each, e.g. ['Payroll processing']. N/A with a reason when no exclusions were defined.",
        question="What is explicitly out of scope for the application, or is nothing excluded?",
        na_allowed=True,
    )
    business_criticality: str = doc_field(
        default='',
        description="How important the application is to the business and what an outage means, e.g. 'Tier 1 - business critical, orders stop without it'. A good value states the tier or level and the reason.",
        question="How business-critical is the application and what happens if it is unavailable?",
    )
    lifecycle_status: str = doc_field(
        default='',
        description="Where the application is in its life, e.g. 'In production', 'Under development' or 'Being retired'. A good value is a short phrase as used by the organisation.",
        question="What is the current lifecycle status of the application?",
    )
    go_live_date: str | NotApplicable | None = doc_field(
        default=None,
        description="Date the application went (or goes) live, ISO format YYYY-MM-DD, e.g. 2024-03-01. N/A with a reason when the application has no go-live date, for example when it is not yet planned.",
        question="On which date did or will the application go live (YYYY-MM-DD)?",
        na_allowed=True,
    )
    technology_summary: str = doc_field(
        default='',
        description="Short plain-language summary of the technology the application is built on, e.g. 'Python web service with a PostgreSQL database, hosted on Azure'. Detail belongs in the architecture facts, not here.",
        question="What is a one-sentence summary of the technology behind the application?",
    )
    related_systems: list[str] = doc_field(
        default_factory=list,
        description="Names of other applications or systems this application depends on or exchanges data with, one per entry, e.g. ['ERP', 'Payment gateway']. Detailed interfaces belong elsewhere.",
        question="Which other systems does the application depend on or exchange data with?",
    )
