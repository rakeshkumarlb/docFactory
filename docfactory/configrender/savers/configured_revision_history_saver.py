from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.shared.revision_history import RevisionHistory


class ConfiguredRevisionHistorySaver(BaseSaver[RevisionHistory]):
    """Saves the RevisionHistory of a configuration-based document."""

    model = RevisionHistory
    key_patterns = ("{app}.Configured.{doctype}.RevisionHistory",)
    table = "ConfiguredDocuments"
