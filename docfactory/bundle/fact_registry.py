"""The facts a bundle can hold: entity name -> model, and the key patterns each accepts (replaces one saver class per entity)."""
from docfactory.entitymodels.facts.application_overview import ApplicationOverview
from docfactory.entitymodels.facts.architecture import Architecture
from docfactory.entitymodels.facts.backup_recovery import BackupRecovery
from docfactory.entitymodels.facts.deployment import Deployment
from docfactory.entitymodels.facts.environments import Environments
from docfactory.entitymodels.facts.functional_requirements import FunctionalRequirements
from docfactory.entitymodels.facts.known_errors import KnownErrors
from docfactory.entitymodels.facts.kpis import Kpis
from docfactory.entitymodels.facts.monitoring import Monitoring
from docfactory.entitymodels.facts.non_functional_requirements import NonFunctionalRequirements
from docfactory.entitymodels.facts.note import Note
from docfactory.entitymodels.facts.slo import Slo
from docfactory.entitymodels.facts.sop import Sop
from docfactory.entitymodels.facts.support import Support
from docfactory.key_patterns import pattern_matches

# Which fact name a "<FactName>.<field>" binding loads, and whether it is Shared (AppID NULL) or application-specific.
FACT_SPECS = {
    "ApplicationOverview": {"model": ApplicationOverview, "shared": False},
    "Kpis": {"model": Kpis, "shared": True},
    "Architecture": {"model": Architecture, "shared": False},
    "BackupRecovery": {"model": BackupRecovery, "shared": False},
    "Deployment": {"model": Deployment, "shared": False},
    "Environments": {"model": Environments, "shared": False},
    "FunctionalRequirements": {"model": FunctionalRequirements, "shared": False},
    "KnownErrors": {"model": KnownErrors, "shared": False},
    "Monitoring": {"model": Monitoring, "shared": False},
    "NonFunctionalRequirements": {"model": NonFunctionalRequirements, "shared": False},
    "Slo": {"model": Slo, "shared": True},
    "Sop": {"model": Sop, "shared": False},
    "Support": {"model": Support, "shared": False},
    "Note": {"model": Note, "shared": False, "taggable": False},  # written by discovery from untagged chunks; never a tagging target
}


def key_patterns_of(entity: str) -> tuple[str, ...]:
    """The key patterns of an entity: Shared.<Entity> for shared facts, else <App>.<Entity> and <App>.Components.<Component>.<Entity>."""
    if FACT_SPECS[entity]["shared"]:
        return (f"Shared.{entity}",)
    return (f"{{app}}.{entity}", f"{{app}}.Components.{{component}}.{entity}")


def entity_of_key(key) -> str | None:
    """The entity name a key belongs to, or None when the key matches no entity's pattern."""
    if not isinstance(key, str):
        return None
    entity = key.rsplit(".", 1)[-1]
    if entity in FACT_SPECS and any(pattern_matches(pattern, key) for pattern in key_patterns_of(entity)):
        return entity
    return None


def taggable_entity_names() -> list[str]:
    """The facts a chunk can be tagged with during ingestion (all but those marked `taggable: False`, such as Note), ordered by name."""
    return sorted(name for name, spec in FACT_SPECS.items() if spec.get("taggable", True))


def entity_names() -> list[str]:
    """Every fact entity name, ordered by name."""
    return sorted(FACT_SPECS)


def shared_entities() -> set[str]:
    """The entities stored only under `Shared.` keys (common to all applications)."""
    return {name for name, spec in FACT_SPECS.items() if spec["shared"]}
