from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.kpis import Kpis


class KpisSaver(BaseSaver[Kpis]):
    """Saves Kpis objects."""

    model = Kpis
    key_patterns = ("Shared.Kpis",)
