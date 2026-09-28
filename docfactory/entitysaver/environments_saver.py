from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.environments import Environments


class EnvironmentsSaver(BaseSaver[Environments]):
    """Saves Environments objects."""

    model = Environments
    key_patterns = ("{app}.Environments", "{app}.Components.{component}.Environments")
