from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements


class FunctionalRequirementsSaver(BaseSaver[FunctionalRequirements]):
    """Saves FunctionalRequirements objects."""

    model = FunctionalRequirements
    key_patterns = ("{app}.FunctionalRequirements", "{app}.Components.{component}.FunctionalRequirements")
