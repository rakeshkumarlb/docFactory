from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from docfactory.models.file_action import FileAction


class CompareResult(DocFactoryModel):
    """Result of comparing an incoming file with DocStore at a target path. Read-only: nothing was written."""

    target_path: str = doc_field(
        description="DocStore-relative path the file would be stored at, forward slashes, e.g. 'ReadmeForge/ReadmeForge SRS v0.3.pdf'.",
        question="What DocStore-relative target path was compared?",
        min_length=1,
    )
    action: FileAction = doc_field(
        description="NEW when DocStore has no row at the target path, SAME when the SHA-256 is identical (storing would be a no-op), CHANGED when it differs (storing would replace the file and bump the version), e.g. CHANGED.",
        question="Is the file NEW, SAME or CHANGED against DocStore?",
    )
    incoming_hashcode: str = doc_field(
        description="SHA-256 hex of the incoming file bytes, e.g. 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'.",
        question="What is the SHA-256 hex of the incoming file?",
        min_length=1,
    )
    stored_hashcode: str | None = doc_field(
        default=None,
        description="SHA-256 hex of the file currently stored at the target path. None when action is NEW, e.g. 'e3b0c442...'.",
        question="What is the SHA-256 hex of the stored file, if any?",
    )
    stored_version: int | None = doc_field(
        default=None,
        description="Version of the stored file in DocStore, starting at 1. None when action is NEW, e.g. 2.",
        question="What is the stored version of the file, if any?",
    )
