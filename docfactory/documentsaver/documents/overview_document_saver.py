from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.documents.overview_document import OverviewDocument


class OverviewDocumentSaver(BaseSaver[OverviewDocument]):
    """Saves OverviewDocument objects."""

    model = OverviewDocument
    key_patterns = ("{app}.Outputs.Overview",)
