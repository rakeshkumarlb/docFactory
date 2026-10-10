from docfactory.base_saver import BaseSaver
from docfactory.documentmodels.missing_info import MissingInfo


class MissingInfoSaver(BaseSaver[MissingInfo]):
    """Saves MissingInfo objects."""

    model = MissingInfo
    key_patterns = ("{app}.Outputs.{doctype}.MissingInfo",)
