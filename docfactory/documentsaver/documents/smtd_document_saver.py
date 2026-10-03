from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.documents.smtd_document import SmtdDocument


class SmtdDocumentSaver(BaseSaver[SmtdDocument]):
    """Saves SmtdDocument objects."""

    model = SmtdDocument
    key_patterns = ("{app}.Outputs.SMTD",)
