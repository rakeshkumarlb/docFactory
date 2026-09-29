from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.facts.sop import Sop


class SopSaver(BaseSaver[Sop]):
    """Saves Sop objects."""

    model = Sop
    key_patterns = ("{app}.Sop", "{app}.Components.{component}.Sop")
