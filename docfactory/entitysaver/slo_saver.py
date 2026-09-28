from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.slo import Slo


class SloSaver(BaseSaver[Slo]):
    """Saves Slo objects."""

    model = Slo
    key_patterns = ("Shared.Slo",)
