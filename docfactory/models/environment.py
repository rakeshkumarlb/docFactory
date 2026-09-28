from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable


class Environment(DocFactoryModel):
    """One deployment environment of an application (e.g. Development, Test, Production) with its purpose, hosting and access control."""

    name: str = doc_field(
        description="Name of the environment, e.g. 'Production' or 'UAT'. Identifies the environment.",
        question="What is the name of this environment?",
        min_length=1,
    )
    purpose: str = doc_field(
        default='',
        description="What the environment is used for, e.g. 'User acceptance testing before release.' Leave empty when not yet described.",
        question="What is this environment used for?",
    )
    hosting: str = doc_field(
        default='',
        description="Where and on what the environment runs, e.g. 'AWS eu-west-1, ECS Fargate'. Leave empty when not yet known.",
        question="Where is this environment hosted?",
    )
    url: str | NotApplicable | None = doc_field(
        default=None,
        description="Base URL of the environment, e.g. 'https://app.example.test'. N/A with a reason when the environment has no URL, for example a batch-only environment.",
        question="What is the base URL of this environment?",
        na_allowed=True,
    )
    access_control: str = doc_field(
        default='',
        description="Who may access the environment and how access is granted, e.g. 'Developers via SSO group dev-team; read-only for support.' Leave empty when not yet known.",
        question="Who has access to this environment and how is access controlled?",
    )
    notes: str = doc_field(
        default='',
        description="Free-text remarks about the environment, e.g. 'Refreshed from production every Sunday.' Leave empty when there is nothing to add.",
        question="Is there anything else worth noting about this environment?",
    )
