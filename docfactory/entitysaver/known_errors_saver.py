from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.known_errors import KnownErrors


class KnownErrorsSaver(BaseSaver[KnownErrors]):
    """Saves KnownErrors objects."""

    model = KnownErrors
    key_patterns = ("{app}.KnownErrors", "{app}.Components.{component}.KnownErrors")
