from docfactory.models.doc_factory_model import DocFactoryModel
from docfactory.models.doc_field import doc_field


class DeferResult(DocFactoryModel):
    """Result of the defer_file tool: an incoming file left in place because it could not be classified confidently."""

    ok: bool = doc_field(
        description="True when the deferral was recorded, False when the call failed, e.g. True.",
        question="Was the file deferred successfully?",
    )
    path: str = doc_field(
        description="Path of the incoming file left in place, relative to incoming/, forward slashes, e.g. 'unknown report.pdf'.",
        question="Which incoming file was left in place?",
        min_length=1,
    )
    reason: str = doc_field(
        description="Why a human must decide about this file, e.g. 'Cannot tell which application this belongs to; two names appear in the text'.",
        question="Why must a human decide about this file?",
        min_length=1,
    )
