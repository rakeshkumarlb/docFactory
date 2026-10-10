"""How a document binding finds its fact: the fact registry, the key a binding reads, the stored fact and the "answered" rule.

A binding `<Fact>.<field>` of a document template names the fact (FACT_SPECS), `fact_key` gives its KnowledgeFacts key, `load_fact`
reads it and `is_answered` applies the same rule as `completeness.py`. Nothing here invents a value: an absent fact or an
unanswered field is a gap for the caller to report.
"""
import json

from docfactory import db
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
from docfactory.entitymodels.facts.slo import Slo
from docfactory.entitymodels.facts.sop import Sop
from docfactory.entitymodels.facts.support import Support
from docfactory.models.not_applicable import NotApplicable

# Which fact name a "<FactName>.<field>" binding loads, and whether it is Shared (AppID NULL) or
# application-specific. A registry that discovers this from the entity savers themselves is Phase 2.
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
}


class BuildError(Exception):
    """Raised when a binding names a fact that FACT_SPECS does not know (a wrongly wired template)."""


def fact_key(app_id: str, fact_name: str) -> str:
    """The KnowledgeFacts key a binding's fact name reads: Shared.<Fact> for shared facts, else <App>.<Fact>."""
    spec = FACT_SPECS.get(fact_name)
    if spec is None:
        raise BuildError(f"cannot load fact {fact_name!r}; add it to FACT_SPECS")
    return f"Shared.{fact_name}" if spec["shared"] else f"{app_id}.{fact_name}"


def load_fact(app_id: str, fact_name: str, cache: dict):
    """The stored fact object for `fact_name`, or None when no row exists. Cached in `cache` (one dict per caller run)."""
    if fact_name not in cache:
        row = db.get_row("KnowledgeFacts", fact_key(app_id, fact_name))
        cache[fact_name] = FACT_SPECS[fact_name]["model"].model_validate(json.loads(row["Value"])) if row else None
    return cache[fact_name]


def is_answered(source_field, value) -> bool:
    """A source field is answered when it is mandatory (guaranteed by validation), holds a NotApplicable, or differs from its own default."""
    if isinstance(value, NotApplicable) or source_field.is_required():
        return True
    return value != source_field.get_default(call_default_factory=True)
