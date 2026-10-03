from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field
from pydantic import NonNegativeInt


class FileInfo(DocFactoryModel):
    """One file waiting in incoming/, as listed by the list_incoming tool: where it is, how big, and its SHA-256."""

    path: str = doc_field(
        description="Path of the file relative to incoming/, forward slashes, including the file name, e.g. 'ReadmeForge SRS v0.3.pdf'.",
        question="What is the path of the file relative to incoming/?",
        min_length=1,
    )
    size_bytes: NonNegativeInt = doc_field(
        description="Size of the file in bytes, zero or more, e.g. 20480.",
        question="How many bytes is the file?",
    )
    hashcode: str = doc_field(
        description="SHA-256 of the file bytes as 64 lowercase hex characters, e.g. 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'.",
        question="What is the SHA-256 hex of the file bytes?",
        min_length=1,
    )
