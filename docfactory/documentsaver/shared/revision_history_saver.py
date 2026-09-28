from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.shared.revision_history import RevisionHistory


class RevisionHistorySaver(BaseSaver[RevisionHistory]):
    """Saves RevisionHistory objects."""

    model = RevisionHistory
    key_patterns = ("{app}.Outputs.{doctype}.RevisionHistory",)
