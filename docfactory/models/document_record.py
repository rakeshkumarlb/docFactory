from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class DocumentRecord(DocFactoryModel):
    """One stored DocumentOutputs row as returned by the typed read: the validated document part as canonical JSON plus its bookkeeping."""

    key: str = doc_field(
        description="The document key, e.g. ReadmeForge.Outputs.SMTD.",
        question="What is the key of the document?",
        min_length=1,
    )
    value: str = doc_field(
        description="The canonical JSON text of the validated document, e.g. '{\"name\":\"x\"}'.",
        question="What is the stored JSON value?",
    )
    hashcode: str = doc_field(
        description="SHA-256 hex of the canonical value, e.g. a 64-character hex string.",
        question="What is the hash of the stored value?",
    )
    completeness: float = doc_field(
        description="How much of the document has been answered, 0 to 100, e.g. 62.5.",
        question="How complete is the stored document?",
    )
    version: int = doc_field(
        description="Number of changes to the row, starting at 1, e.g. 3.",
        question="Which version is the stored document?",
    )
    app_id: str | None = doc_field(
        default=None,
        description="The application the document belongs to, e.g. ReadmeForge. None for shared documents.",
        question="Which application does this document belong to?",
    )
