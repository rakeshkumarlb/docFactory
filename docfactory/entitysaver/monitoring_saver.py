from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.facts.monitoring import Monitoring


class MonitoringSaver(BaseSaver[Monitoring]):
    """Saves Monitoring objects."""

    model = Monitoring
    key_patterns = ("{app}.Monitoring", "{app}.Components.{component}.Monitoring")
