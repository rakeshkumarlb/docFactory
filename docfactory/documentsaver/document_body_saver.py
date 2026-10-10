from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.document_body import DocumentBody


class DocumentBodySaver(BaseSaver[DocumentBody]):
    """Saves the body of a generated document."""

    model = DocumentBody
    key_patterns = ("{app}.Outputs.{doctype}",)
