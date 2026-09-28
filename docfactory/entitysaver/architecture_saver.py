from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.architecture import Architecture


class ArchitectureSaver(BaseSaver[Architecture]):
    """Saves Architecture objects."""

    model = Architecture
    key_patterns = ("{app}.Architecture", "{app}.Components.{component}.Architecture")
