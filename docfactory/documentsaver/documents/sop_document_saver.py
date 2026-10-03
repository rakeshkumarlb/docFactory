from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.documents.sop_document import SopDocument


class SopDocumentSaver(BaseSaver[SopDocument]):
    """Saves SopDocument objects."""

    model = SopDocument
    key_patterns = ("{app}.Outputs.SOP",)
