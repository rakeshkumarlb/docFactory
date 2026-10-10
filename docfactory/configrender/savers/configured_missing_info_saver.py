from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.shared.missing_info import MissingInfo


class ConfiguredMissingInfoSaver(BaseSaver[MissingInfo]):
    """Saves the MissingInfo (needs list) of a configuration-based document."""

    model = MissingInfo
    key_patterns = ("{app}.Configured.{doctype}.MissingInfo",)
    table = "ConfiguredDocuments"
