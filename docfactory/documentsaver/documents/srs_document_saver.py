from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.documents.srs_document import SrsDocument


class SrsDocumentSaver(BaseSaver[SrsDocument]):
    """Saves SrsDocument objects."""

    model = SrsDocument
    key_patterns = ("{app}.Outputs.SRS",)
