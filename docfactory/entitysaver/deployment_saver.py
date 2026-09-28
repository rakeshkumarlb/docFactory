from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.deployment import Deployment


class DeploymentSaver(BaseSaver[Deployment]):
    """Saves Deployment objects."""

    model = Deployment
    key_patterns = ("{app}.Deployment", "{app}.Components.{component}.Deployment")
