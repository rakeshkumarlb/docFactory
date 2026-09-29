from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class Deployment(DocFactoryModel):
    """How an application is built, released and rolled back."""

    release_process: str = doc_field(
        default='',
        description="How a release goes from approved change to production, e.g. 'Merge to main, pipeline builds and deploys to UAT, manual approval promotes to production.' Leave empty when not yet described.",
        question="How is a release performed?",
    )
    ci_cd_tooling: str = doc_field(
        default='',
        description="The build and deployment tooling, e.g. 'GitHub Actions and Terraform'. Leave empty when not yet known.",
        question="Which CI/CD tooling is used?",
    )
    release_frequency: str = doc_field(
        default='',
        description="How often releases happen, e.g. 'Every two weeks'. Leave empty when not yet known.",
        question="How often is the application released?",
    )
    rollback_procedure: str = doc_field(
        default='',
        description="How a failed release is rolled back, e.g. 'Redeploy the previous tagged image via the pipeline.' Leave empty when not yet defined.",
        question="How is a failed release rolled back?",
    )
    configuration_management: str = doc_field(
        default='',
        description="How configuration and secrets are managed per environment, e.g. 'Environment variables from a secrets manager.' Leave empty when not yet known.",
        question="How are configuration and secrets managed?",
    )
