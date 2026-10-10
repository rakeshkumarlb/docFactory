from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.shared.document_control import DocumentControl


class ConfiguredDocumentControlSaver(BaseSaver[DocumentControl]):
    """Saves the DocumentControl of a configuration-based document."""

    model = DocumentControl
    key_patterns = ("{app}.Configured.{doctype}.DocumentControl",)
    table = "ConfiguredDocuments"
