from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.facts.support import Support


class SupportSaver(BaseSaver[Support]):
    """Saves Support objects."""

    model = Support
    key_patterns = ("{app}.Support", "{app}.Components.{component}.Support")
