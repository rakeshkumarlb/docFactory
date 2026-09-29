from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.facts.application_overview import ApplicationOverview


class ApplicationOverviewSaver(BaseSaver[ApplicationOverview]):
    """Saves ApplicationOverview objects."""

    model = ApplicationOverview
    key_patterns = ("{app}.ApplicationOverview", "{app}.Components.{component}.ApplicationOverview")
