from docfactory.base_saver import BaseSaver
from docfactory.models.configured_body import ConfiguredBody


class ConfiguredBodySaver(BaseSaver[ConfiguredBody]):
    """Saves ConfiguredBody objects."""

    model = ConfiguredBody
    key_patterns = ("{app}.Configured.{doctype}",)
    table = "ConfiguredDocuments"
