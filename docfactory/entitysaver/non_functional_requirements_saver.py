from docfactory.base_saver import BaseSaver
from docfactory.entitymodels.facts.non_functional_requirements import NonFunctionalRequirements


class NonFunctionalRequirementsSaver(BaseSaver[NonFunctionalRequirements]):
    """Saves NonFunctionalRequirements objects."""

    model = NonFunctionalRequirements
    key_patterns = ("{app}.NonFunctionalRequirements", "{app}.Components.{component}.NonFunctionalRequirements")
