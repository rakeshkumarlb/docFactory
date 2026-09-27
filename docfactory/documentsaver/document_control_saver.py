from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.document_control import DocumentControl


class DocumentControlSaver(BaseSaver[DocumentControl]):
    """Saves DocumentControl objects."""

    model = DocumentControl
    key_patterns = ("{app}.Outputs.{doctype}.DocumentControl",)
