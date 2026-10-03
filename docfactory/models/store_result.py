from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.file_action import FileAction


class StoreResult(DocFactoryModel):
    """Result of the store_file tool: whether the file was moved into DocStore and what happened, or why it failed."""

    ok: bool = doc_field(
        description="True when the file was stored (or was already identical), False when the call failed and nothing changed, e.g. True.",
        question="Did the store succeed?",
    )
    target_path: str = doc_field(
        description="DocStore-relative path the store was attempted at, forward slashes, e.g. 'ReadmeForge/ReadmeForge SRS v0.3.pdf'.",
        question="What DocStore-relative target path was used?",
        min_length=1,
    )
    action: FileAction | None = doc_field(
        default=None,
        description="NEW, SAME or CHANGED describing what the store did. None when ok is False, e.g. FileAction.CHANGED.",
        question="Was the stored file NEW, SAME or CHANGED?",
    )
    version: int | None = doc_field(
        default=None,
        description="DocStore version of the file after the store, starting at 1. None when not ok, e.g. 2.",
        question="What is the version of the stored file?",
    )
    sidecar_path: str | None = doc_field(
        default=None,
        description="Path of the markdown text sidecar relative to DocStore/, forward slashes. None when no sidecar was written, e.g. 'ReadmeForge/ReadmeForge SRS v0.3.pdf.md'.",
        question="Where is the text sidecar stored, if any?",
    )
    error: str | None = doc_field(
        default=None,
        description="Why the store failed, precise enough to fix the call, e.g. 'incoming file not found: test-file.txt'. None when ok.",
        question="Why did the store fail, if it did?",
    )
