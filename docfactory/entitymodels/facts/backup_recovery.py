from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.not_applicable import NotApplicable


class BackupRecovery(DocFactoryModel):
    """How an application's data is backed up and restored, and its recovery objectives."""

    backup_schedule: str | NotApplicable | None = doc_field(
        default=None,
        description="When backups run, e.g. 'Nightly at 02:00 UTC'. N/A with a reason when the application is stateless and needs no backup.",
        question="When are backups taken?",
        na_allowed=True,
    )
    backup_retention: str | NotApplicable | None = doc_field(
        default=None,
        description="How long backups are kept, e.g. '35 days'. N/A with a reason when no backups are taken.",
        question="How long are backups retained?",
        na_allowed=True,
    )
    backup_location: str | NotApplicable | None = doc_field(
        default=None,
        description="Where backups are stored, e.g. 'Encrypted S3 bucket in a second region'. N/A with a reason when no backups are taken.",
        question="Where are backups stored?",
        na_allowed=True,
    )
    restore_procedure: str | NotApplicable | None = doc_field(
        default=None,
        description="How data is restored from backup, e.g. 'Restore the latest snapshot via the runbook RB-12.' N/A with a reason when nothing needs restoring.",
        question="How is data restored from a backup?",
        na_allowed=True,
    )
    rpo: str = doc_field(
        default='',
        description="Recovery Point Objective, the maximum acceptable data loss, e.g. '24 hours'. Leave empty when not yet defined.",
        question="What is the recovery point objective (RPO)?",
    )
    rto: str = doc_field(
        default='',
        description="Recovery Time Objective, the maximum acceptable downtime, e.g. '4 hours'. Leave empty when not yet defined.",
        question="What is the recovery time objective (RTO)?",
    )
    disaster_recovery_plan: str = doc_field(
        default='',
        description="Summary of, or relative path to, the disaster recovery plan, e.g. 'docs/dr-plan.md'. Leave empty when not yet defined.",
        question="What is the disaster recovery plan?",
    )
