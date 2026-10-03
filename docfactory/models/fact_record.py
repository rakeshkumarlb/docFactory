from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.fact_status import FactStatus
from docfactory.models.fact_verification import FactVerification


class FactRecord(DocFactoryModel):
    """One stored KnowledgeFacts row as returned by the typed read functions: the validated fact as canonical JSON plus its bookkeeping and OKF metadata."""

    key: str = doc_field(
        description="The fact key, <Scope>.<Name>[.<SubName>...], e.g. ReadmeForge.Architecture.",
        question="What is the key of the fact?",
    )
    value: str = doc_field(
        description="The canonical JSON text of the validated fact, e.g. '{\"name\":\"x\"}'.",
        question="What is the stored JSON value?",
    )
    hashcode: str = doc_field(
        description="SHA-256 hex of the canonical value, e.g. a 64-character hex string.",
        question="What is the hash of the stored value?",
    )
    completeness: float = doc_field(
        description="How much of the fact has been answered, 0 to 100, e.g. 62.5.",
        question="How complete is the stored fact?",
    )
    version: int = doc_field(
        description="Number of changes to the row, starting at 1, e.g. 3.",
        question="Which version is the stored fact?",
    )
    app_id: str | None = doc_field(
        default=None,
        description="The application the fact belongs to, e.g. ReadmeForge. None for shared facts.",
        question="Which application does this fact belong to?",
    )
    file_path: str | None = doc_field(
        default=None,
        description="Path of the OKF bundle file under bundles/, forward slashes, e.g. ReadmeForge/Architecture.md. None when no file was written.",
        question="Where is the bundle file?",
    )
    frontmatter: str | None = doc_field(
        default=None,
        description="The OKF YAML frontmatter text of the fact, e.g. 'type: Architecture'. None when not generated.",
        question="What is the frontmatter text?",
    )
    generated_by: str | None = doc_field(
        default=None,
        description="The actor that produced the fact, '<producer>/<version>', e.g. seed. None when unknown.",
        question="Who produced this fact?",
    )
    generated_at: str | None = doc_field(
        default=None,
        description="When the fact was produced, ISO 8601 datetime with explicit UTC offset, e.g. 2026-06-30T14:00:00Z. None when unknown.",
        question="When was this fact produced?",
        pattern="^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$",
    )
    verified: list[FactVerification] = doc_field(
        default_factory=list,
        description="Verification events, empty while the fact is unverified, e.g. one FactVerification by human:test-user.",
        question="Who has verified this fact?",
    )
    status: FactStatus = doc_field(
        default=FactStatus.DRAFT,
        description="Lifecycle status of the fact: draft, stable or deprecated, e.g. draft.",
        question="What is the lifecycle status of this fact?",
    )
    stale_after: str | None = doc_field(
        default=None,
        description="When the fact should be re-checked, ISO 8601 datetime with explicit UTC offset, e.g. 2026-12-31T00:00:00Z. None when it has no expiry.",
        question="After when should this fact be re-checked?",
        pattern="^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})$",
    )
